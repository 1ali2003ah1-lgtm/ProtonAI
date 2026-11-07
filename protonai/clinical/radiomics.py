"""Radiomic feature extraction and tumor classification for proton therapy.
Designed & developed by: Ali Hussein Thajil

Implements:
- Tumor group classification based on radiomic features
- Treatment protocol recommendation for proton therapy
- Integration with ProtonAI clinical decision support system
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import joblib
import os

# Treatment protocols mapped to tumor groups
TREATMENT_PROTOCOLS: Dict[int, Dict] = {
    0: {
        "name": "Focused High-Dose Proton Beam",
        "description": "Small, dense tumors requiring precise targeted radiation",
        "dose_gy": 74.0,
        "fractions": 37,
        "beam_arrangement": "IMPT",
        "robustness_margin_mm": 3.0,
    },
    1: {
        "name": "Wide-Field High-Dose Proton Beam", 
        "description": "Large, solid tumors requiring wide coverage",
        "dose_gy": 70.0,
        "fractions": 35,
        "beam_arrangement": "PSPT",
        "robustness_margin_mm": 5.0,
    },
    2: {
        "name": "Standard Proton Beam Protocol",
        "description": "Moderate soft tumors responding to standard protocol",
        "dose_gy": 66.0,
        "fractions": 33,
        "beam_arrangement": "IMPT",
        "robustness_margin_mm": 4.0,
    },
}

FEATURE_NAMES: List[str] = [
    "volume_voxels", "tumor_slices", "max_slice_area",
    "mean_HU", "std_HU", "min_HU", "max_HU", "median_HU",
    "p10_HU", "p25_HU", "p75_HU", "p90_HU",
    "skewness", "kurtosis", "energy", "uniformity",
    "entropy", "iqr_HU", "range_HU",
]


@dataclass
class RadiomicFeatures:
    volume_voxels: float
    tumor_slices: float
    max_slice_area: float
    mean_HU: float
    std_HU: float
    min_HU: float
    max_HU: float
    median_HU: float
    p10_HU: float
    p25_HU: float
    p75_HU: float
    p90_HU: float
    skewness: float
    kurtosis: float
    energy: float
    uniformity: float
    entropy: float
    iqr_HU: float
    range_HU: float

    def to_array(self) -> np.ndarray:
        return np.array([getattr(self, f) for f in FEATURE_NAMES])


@dataclass
class TreatmentRecommendation:
    tumor_group: int
    protocol_name: str
    description: str
    dose_gy: float
    fractions: int
    beam_arrangement: str
    robustness_margin_mm: float
    confidence_score: float


class RadiomicsClassifier:
    """Tumor classifier for proton therapy treatment planning."""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.classifier = None
        self.scaler = None
        self.pca = None
        self._load_models()

    def _load_models(self) -> None:
        try:
            self.classifier = joblib.load(
                os.path.join(self.models_dir, "tumor_classifier.pkl")
            )
            self.scaler = joblib.load(
                os.path.join(self.models_dir, "scaler.pkl")
            )
            self.pca = joblib.load(
                os.path.join(self.models_dir, "pca.pkl")
            )
        except FileNotFoundError as e:
            raise RuntimeError(f"Model files not found: {e}")

    def _preprocess(self, features: np.ndarray) -> np.ndarray:
        scaled = self.scaler.transform(features.reshape(1, -1))
        return scaled

    def classify(self, features: RadiomicFeatures) -> TreatmentRecommendation:
        arr = features.to_array()
        processed = self._preprocess(arr)
        group = int(self.classifier.predict(processed)[0])
        distances = self.classifier.transform(processed)
        min_dist = distances[0, group]
        max_dist = distances.max()
        confidence = float(1.0 - (min_dist / (max_dist + 1e-10)))
        confidence = round(min(max(confidence, 0.0), 1.0), 3)
        protocol = TREATMENT_PROTOCOLS[group]
        return TreatmentRecommendation(
            tumor_group=group,
            protocol_name=protocol["name"],
            description=protocol["description"],
            dose_gy=protocol["dose_gy"],
            fractions=protocol["fractions"],
            beam_arrangement=protocol["beam_arrangement"],
            robustness_margin_mm=protocol["robustness_margin_mm"],
            confidence_score=confidence,
        )

    def classify_from_dict(self, data: Dict) -> TreatmentRecommendation:
        features = RadiomicFeatures(**{k: data[k] for k in FEATURE_NAMES})
        return self.classify(features)
