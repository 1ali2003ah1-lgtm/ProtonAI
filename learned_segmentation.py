"""
ProtonAI - Learned Segmentation
نموذج تقسيم متعلّم حقيقي: مصنف بكسلات (RandomForest على شدة HU)
fit(hu, labels) ← يتدرّب | segment(hu) ← يتنبأ | save/load ← يُحفظ ويُحمّل
يشغّل مقبس pretrained_segmenter (نفس الواجهة). السياق المكاني/torch على الجهاز لاحقاً
"""

import pickle
import logging
import numpy as np
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger("ProtonAI.LearnedSegmentation")


class LearnedSegmenter:
    """
    مقسّم متعلّم.
    - fit: يتدرّب على (HU, أقنعة معنونة).
    - segment: يتنبأ بقناع الورم (bool).
    - save / load: حفظ/تحميل النموذج (pickle).
    الميزة الحالية: شدة HU للبكسل (سياق مكاني لاحقاً).
    """

    def __init__(self, n_estimators: int = 50, seed: int = 42):
        if n_estimators < 1:
            raise ValueError("n_estimators يجب أن يكون >= 1")
        self.model = RandomForestClassifier(
            n_estimators=n_estimators, random_state=seed)
        self.fitted = False

    def _features(self, hu: np.ndarray) -> np.ndarray:
        """ميزات بكسلية: شدة HU (عمود واحد لكل بكسل)"""
        return np.asarray(hu, dtype=float).reshape(-1, 1)

    def fit(self, hu: np.ndarray, labels: np.ndarray) -> "LearnedSegmenter":
        """تدريب على صورة HU + قناع معنون (0/1) بنفس الأبعاد"""
        hu = np.asarray(hu, dtype=float)
        labels = np.asarray(labels)
        if hu.shape != labels.shape:
            raise ValueError(f"أبعاد HU {hu.shape} != الأقنعة {labels.shape}")
        if hu.size == 0:
            raise ValueError("المدخلات فارغة")
        self.model.fit(self._features(hu), labels.astype(int).reshape(-1))
        self.fitted = True
        logger.info(f"تم تدريب المقسّم على {hu.size} بكسل")
        return self

    def segment(self, hu: np.ndarray) -> np.ndarray:
        """التنبؤ بقناع الورم (bool) بنفس أبعاد الدخل"""
        if not self.fitted:
            raise ValueError("النموذج غير مدرّب — استدعِ fit أولاً")
        hu = np.asarray(hu, dtype=float)
        pred = self.model.predict(self._features(hu))
        return (pred == 1).reshape(hu.shape)

    def save(self, path) -> None:
        """حفظ النموذج"""
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "fitted": self.fitted}, f)

    @classmethod
    def load(cls, path) -> "LearnedSegmenter":
        """تحميل نموذج محفوظ"""
        with open(path, "rb") as f:
            d = pickle.load(f)
        obj = cls.__new__(cls)  # بناء بدون __init__
        obj.model = d["model"]
        obj.fitted = d["fitted"]
        return obj
