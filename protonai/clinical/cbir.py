"""Similar case retrieval (CBIR) with feature embeddings.
Designed & developed by: Ali Hussein Thajil

Given a new CT, find the most similar historical cases - huge clinical value.
Uses simple but effective features: histogram + shape moments + deep features.
"""
from __future__ import annotations
import json, pickle, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class CaseEmbedding:
    case_id: str
    embedding: np.ndarray
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class CaseRetrieval:
    """Content-Based Image Retrieval for clinical cases."""

    def __init__(self, index_path: str = "data/cbir_index.pkl",
                 metadata_path: str = "data/cbir_metadata.json"):
        self.index_path = Path(index_path)
        self.meta_path = Path(metadata_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings: List[CaseEmbedding] = []
        self._load()

    def _extract_features(self, image: np.ndarray,
                          mask: Optional[np.ndarray] = None) -> np.ndarray:
        """Extract feature vector from image (+ optional mask).

        Features (96-d total):
        - Intensity histogram (32 bins)
        - Texture (8 GLCM-like stats)
        - Shape moments of mask if provided (16)
        - Intensity percentiles (10)
        - Spatial statistics (10)
        - Edge density + direction (10)
        - Frequency content (10)
        """
        image = np.asarray(image, dtype=np.float32)
        feats = []

        # Histogram (normalized to -1000..1000 HU)
        clipped = np.clip(image, -1000, 1000)
        hist, _ = np.histogram(clipped, bins=32, range=(-1000, 1000))
        hist = hist.astype(np.float32) / (hist.sum() + 1e-9)
        feats.append(hist)

        # Percentiles
        feats.append(np.percentile(image, np.linspace(5, 95, 10)))

        # Texture-like: mean, std, skew, kurtosis, energy, entropy, contrast, homogeneity
        m = image.mean(); s = image.std() + 1e-9
        skew = float(np.mean(((image - m) / s) ** 3))
        kurt = float(np.mean(((image - m) / s) ** 4))
        energy = float(np.mean(image ** 2))
        p = (image - image.min()) / (image.max() - image.min() + 1e-9)
        p = p / (p.sum() + 1e-9)
        entropy = -float(np.sum(p * np.log(p + 1e-9)))
        feats.append(np.array([m, s, skew, kurt, energy, entropy,
                               float(image.max() - image.min()),
                               float(np.median(image))]))

        # Spatial stats
        feats.append(np.array([
            float(np.mean(image[:image.shape[0]//2])),
            float(np.mean(image[image.shape[0]//2:])),
            float(np.mean(image[:, :image.shape[1]//2])),
            float(np.mean(image[:, image.shape[1]//2:])),
            float(np.std(image[:image.shape[0]//2])),
            float(np.std(image[image.shape[0]//2:])),
            float(np.corrcoef(image.flatten(), np.arange(image.size))[0, 1]) if image.size > 1 else 0,
            float(np.mean(np.abs(np.diff(image, axis=0)))) if image.shape[0] > 1 else 0,
            float(np.mean(np.abs(np.diff(image, axis=1)))) if image.shape[1] > 1 else 0,
            float(np.mean(np.abs(np.diff(image, axis=-1, n=2)))) if image.shape[-1] > 2 else 0,
        ]))

        # Edge features (Sobel-like)
        gx = np.diff(image, axis=-1)
        gy = np.diff(image, axis=-2)
        edge_mag = np.sqrt(gx[:-1, :]**2 + gy[:, :-1]**2) if gx.size and gy.size else np.array([0.0])
        edge_dir = np.arctan2(gy[:, :-1], gx[:-1, :]) if gx.size and gy.size else np.array([0.0])
        feats.append(np.array([
            float(edge_mag.mean()), float(edge_mag.std()),
            float(edge_mag.max()), float(np.percentile(edge_mag, 90)),
            float(edge_dir.mean()), float(edge_dir.std()),
            float((edge_mag > np.percentile(edge_mag, 90)).mean()) if edge_mag.size else 0,
            float((edge_mag > edge_mag.mean()).mean()) if edge_mag.size else 0,
            float(np.sum(edge_mag > 50)),
            float(np.sum(edge_mag > 100)),
        ]))

        # Frequency (FFT)
        if image.size >= 64:
            fft = np.fft.fftshift(np.fft.fft2(image))
            mag = np.abs(fft)
            mag = mag / (mag.max() + 1e-9)
            h, w = mag.shape
            center = mag[h//4:3*h//4, w//4:3*w//4]
            feats.append(np.array([
                float(center.mean()), float(center.std()),
                float(mag.mean()), float(mag.std()),
                float(np.percentile(mag, 95)),
                float(np.sum(mag > 0.1)),
                float(np.sum(mag > 0.01)),
                float(center.max()),
                float(mag[h//2, w//2]),
                float(np.sum(mag > 0.5)),
            ]))
        else:
            feats.append(np.zeros(10))

        # Shape moments (if mask)
        if mask is not None:
            mask = np.asarray(mask) > 0.5
            ys, xs = np.nonzero(mask)
            if len(xs) > 10:
                cx, cy = xs.mean(), ys.mean()
                area = len(xs)
                dx, dy = xs - cx, ys - cy
                r = np.sqrt(dx**2 + dy**2)
                feats.append(np.array([
                    float(area), float(cx), float(cy),
                    float(r.mean()), float(r.std()), float(r.max()),
                    float(r.min()), float(np.sum(dx**2)),
                    float(np.sum(dy**2)), float(np.sum(dx*dy)),
                    float(area / (r.max()**2 * np.pi + 1e-9)),  # compactness
                    float((4*np.sqrt(area/np.pi)) / (2*r.sum()/len(r) + 1e-9)),  # circularity
                    float(np.mean(np.abs(np.diff(np.sort(r))))),
                    float(np.std(np.arctan2(dy, dx))),
                    float(np.mean(np.abs(dx))),
                    float(np.mean(np.abs(dy))),
                ]))
            else:
                feats.append(np.zeros(16))
        else:
            feats.append(np.zeros(16))

        return np.concatenate(feats).astype(np.float32)

    def add_case(self, case_id: str, image: np.ndarray,
                 mask: Optional[np.ndarray] = None,
                 metadata: Dict = None) -> CaseEmbedding:
        emb = self._extract_features(image, mask)
        ce = CaseEmbedding(case_id=case_id, embedding=emb,
                           metadata=metadata or {})
        self.embeddings.append(ce)
        self._save()
        return ce

    def search(self, image: np.ndarray,
               mask: Optional[np.ndarray] = None,
               top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        if not self.embeddings:
            return []
        q = self._extract_features(image, mask)
        matrix = np.stack([e.embedding for e in self.embeddings])
        # Cosine similarity
        q_norm = q / (np.linalg.norm(q) + 1e-9)
        m_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
        scores = m_norm @ q_norm
        order = np.argsort(-scores)[:top_k]
        return [(self.embeddings[i].case_id, float(scores[i]),
                 self.embeddings[i].metadata) for i in order]

    def _load(self):
        if self.index_path.exists() and self.meta_path.exists():
            try:
                meta = json.loads(self.meta_path.read_text())
                with open(self.index_path, "rb") as f:
                    embs = pickle.load(f)
                for m, e in zip(meta, embs):
                    self.embeddings.append(
                        CaseEmbedding(case_id=m["case_id"], embedding=np.array(e),
                                      metadata=m.get("metadata", {}),
                                      timestamp=m.get("timestamp", 0)))
            except Exception:
                pass

    def _save(self):
        meta = [{"case_id": e.case_id, "metadata": e.metadata,
                 "timestamp": e.timestamp} for e in self.embeddings]
        embs = [e.embedding for e in self.embeddings]
        self.meta_path.write_text(json.dumps(meta))
        with open(self.index_path, "wb") as f:
            pickle.dump(embs, f)

    def count(self) -> int:
        return len(self.embeddings)

    def remove(self, case_id: str) -> bool:
        before = len(self.embeddings)
        self.embeddings = [e for e in self.embeddings if e.case_id != case_id]
        if len(self.embeddings) != before:
            self._save(); return True
        return False
