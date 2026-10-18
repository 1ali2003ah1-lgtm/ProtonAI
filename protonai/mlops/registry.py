"""Model registry with versioning, staging, and rollback.
Designed & developed by: Ali Hussein Thajil"""
from __future__ import annotations
import hashlib, json, time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional


STAGES = ("dev", "staging", "production", "archived")


@dataclass
class ModelVersion:
    version: str
    stage: str = "dev"
    metrics: Dict[str, float] = field(default_factory=dict)
    artifact_hash: str = ""
    author: str = ""
    description: str = ""
    created_at: float = 0.0
    promoted_at: Optional[float] = None
    parent_version: Optional[str] = None
    dataset_hash: str = ""
    hyperparameters: Dict = field(default_factory=dict)


class ModelRegistry:
    def __init__(self, root: str = "models/registry"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Dict]:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text())
        return {"versions": {}, "production": None, "staging": None}

    def _save(self):
        self.index_path.write_text(json.dumps(self.index, indent=2))

    def register(self, version: str, metrics: Dict[str, float],
                 artifact_path: Optional[str] = None,
                 author: str = "Ali Hussein Thajil",
                 description: str = "",
                 hyperparameters: Dict = None,
                 dataset_hash: str = "",
                 parent_version: Optional[str] = None) -> ModelVersion:
        artifact_hash = ""
        if artifact_path and Path(artifact_path).exists():
            h = hashlib.sha256()
            h.update(Path(artifact_path).read_bytes())
            artifact_hash = h.hexdigest()
        mv = ModelVersion(
            version=version, metrics=metrics, artifact_hash=artifact_hash,
            author=author, description=description, created_at=time.time(),
            parent_version=parent_version, dataset_hash=dataset_hash,
            hyperparameters=hyperparameters or {})
        self.index["versions"][version] = asdict(mv)
        self._save()
        return mv

    def promote(self, version: str, stage: str) -> ModelVersion:
        if stage not in STAGES:
            raise ValueError(f"Invalid stage: {stage}")
        if version not in self.index["versions"]:
            raise KeyError(f"Unknown version: {version}")
        mv = self.index["versions"][version]
        mv["stage"] = stage
        mv["promoted_at"] = time.time()
        self.index[stage] = version
        self._save()
        return ModelVersion(**mv)

    def rollback(self, stage: str, to_version: str) -> ModelVersion:
        return self.promote(to_version, stage)

    def get(self, version: str) -> Optional[ModelVersion]:
        d = self.index["versions"].get(version)
        return ModelVersion(**d) if d else None

    def current(self, stage: str = "production") -> Optional[ModelVersion]:
        v = self.index.get(stage)
        return self.get(v) if v else None

    def list_versions(self, stage: Optional[str] = None) -> List[ModelVersion]:
        out = []
        for d in self.index["versions"].values():
            if stage and d["stage"] != stage:
                continue
            out.append(ModelVersion(**d))
        out.sort(key=lambda m: m.created_at, reverse=True)
        return out

    def compare(self, v1: str, v2: str) -> Dict:
        m1, m2 = self.get(v1), self.get(v2)
        if not m1 or not m2:
            raise KeyError("version not found")
        return {"v1": asdict(m1), "v2": asdict(m2),
                "metrics_diff": {k: m1.metrics.get(k, 0) - m2.metrics.get(k, 0)
                                  for k in set(m1.metrics) | set(m2.metrics)}}
