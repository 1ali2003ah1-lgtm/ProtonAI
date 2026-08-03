"""
ProtonAI - Torch Segmenter (Device Phase)
تقسيم CNN مكاني حقيقي بـ torch: يقرأ سياق الجيران (أدق من مصنف البكسل)
الاستيراد محروس: بدون torch → CI يتخطى الاختبارات بأمان؛ على الجهاز يشتغل
pip install torch  ←  يفعّلها على جهازك
"""

import logging
import numpy as np

logger = logging.getLogger("ProtonAI.TorchSegmenter")

try:  # استيراد محروس — لا يكسر CI بدون torch
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    torch = nn = F = None
    TORCH_AVAILABLE = False


def _require_torch():
    if not TORCH_AVAILABLE:
        raise RuntimeError(
            "torch غير مثبت — ثبّته على جهازك (pip install torch) لتفعيل التقسيم CNN")


class TorchSegmenter:
    """
    مقسّم CNN مكاني (جهاز).
    - fit: يتدرّب على (HU, أقنعة) بـ BCEWithLogits + Adam.
    - segment: يتنبأ بقناع bool (sigmoid > 0.5).
    - save / load: state_dict.
    """

    def __init__(self, lr: float = 1e-2, seed: int = 42):
        _require_torch()
        torch.manual_seed(seed)
        self.lr = lr
        self.net = nn.Sequential(
            nn.Conv2d(1, 8, 3, padding=1), nn.ReLU(),
            nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(),
            nn.Conv2d(16, 1, 1),
        )
        self.fitted = False

    def _to_tensor(self, hu):
        hu = np.asarray(hu, dtype=np.float32)
        hu = (hu - hu.mean()) / (hu.std() + 1e-6)
        return torch.tensor(hu)[None, None]

    def fit(self, hu, labels, epochs: int = 60) -> "TorchSegmenter":
        """تدريب full-batch على صورة معنونة"""
        x = self._to_tensor(hu)
        y = torch.tensor(np.asarray(labels, dtype=np.float32))[None, None]
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        for _ in range(epochs):
            opt.zero_grad()
            loss = F.binary_cross_entropy_with_logits(self.net(x), y)
            loss.backward()
            opt.step()
        self.fitted = True
        logger.info(f"تم تدريب CNN على {np.asarray(hu).size} بكسل")
        return self

    def segment(self, hu) -> np.ndarray:
        """قناع الورم (bool) باستخدام السياق المكاني"""
        if not self.fitted:
            raise ValueError("النموذج غير مدرّب — استدعِ fit أولاً")
        with torch.no_grad():
            prob = torch.sigmoid(self.net(self._to_tensor(hu)))
        return (prob[0, 0].numpy() > 0.5)

    def save(self, path) -> None:
        _require_torch()
        torch.save(self.net.state_dict(), str(path))

    def load(self, path) -> "TorchSegmenter":
        _require_torch()
        self.net.load_state_dict(torch.load(str(path), map_location="cpu"))
        self.fitted = True
        return self
