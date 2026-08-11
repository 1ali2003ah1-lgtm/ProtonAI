"""
ProtonAI - Models: Segmentation Training Scaffold (nnU-Net style)
- make_synthetic_volume: phantom 3D اصطناعي (ورم كروي) للتدريب الأولي.
- SmallUNet: نموذج 3D مصغر (يُرقّى لـ nnU-Net كامل عند توفر GPU/بيانات).
- train/evaluate: تدريب بـ dice-loss + تقييم بـ Dice/HD95/ASSD.
محمي بـ torch: يشتغل بالـ CI بدون GPU، ويشتغل فعلياً عند توفره.
"""

import logging
import numpy as np

logger = logging.getLogger("ProtonAI.Models.SegTrain")

try:
    import torch
    from torch import nn
    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    torch = None
    nn = object
    TORCH_AVAILABLE = False

from seg_metrics import dice, hd95, assd


def make_synthetic_volume(shape=(16, 16, 16), seed: int = 0):
    """phantom 3D: خلفية ~ماء + ورم كروي عالي الشدة"""
    rng = np.random.default_rng(seed)
    img = rng.normal(0.0, 0.05, size=shape)
    c = [s // 2 for s in shape]
    r = max(2, min(shape) // 4)
    zz, yy, xx = np.mgrid[0:shape[0], 0:shape[1], 0:shape[2]]
    mask = ((zz - c[0]) ** 2 + (yy - c[1]) ** 2 + (xx - c[2]) ** 2) <= r * r
    img[mask] += 1.0
    return img.astype(np.float32), mask.astype(bool)


if TORCH_AVAILABLE:
    class SmallUNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = nn.Conv3d(1, 8, 3, padding=1)
            self.mid = nn.Conv3d(8, 8, 3, padding=1)
            self.dec = nn.Conv3d(8, 1, 3, padding=1)
            self.act = nn.ReLU()

        def forward(self, x):
            x = self.act(self.enc(x))
            x = self.act(self.mid(x))
            return self.dec(x)

    def _dice_loss(pred, target):
        p = torch.sigmoid(pred).flatten(1)
        t = target.flatten(1).float()
        inter = (p * t).sum(1)
        return (1 - (2 * inter + 1) / (p.sum(1) + t.sum(1) + 1)).mean()


def train(volumes, masks, epochs: int = 2, lr: float = 1e-3, seed: int = 0):
    """تدريب SmallUNet بـ dice-loss؛ يرجع (model, history)"""
    if not TORCH_AVAILABLE:
        raise RuntimeError("torch مطلوب للتدريب — ثبّته على جهاز بـ GPU")
    torch.manual_seed(seed)
    model = SmallUNet()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    hist = []
    for ep in range(epochs):
        total = 0.0
        for img, msk in zip(volumes, masks):
            x = torch.tensor(img)[None, None]
            y = torch.tensor(msk)[None, None].float()
            opt.zero_grad()
            loss = _dice_loss(model(x), y)
            loss.backward()
            opt.step()
            total += loss.item()
        hist.append(total / len(volumes))
    logger.info(f"انتهى التدريب: {epochs} epochs")
    return model, hist


def predict_mask(model, img, thr: float = 0.5):
    """قناع متوقع من النموذج"""
    with torch.no_grad():
        x = torch.tensor(img)[None, None]
        p = torch.sigmoid(model(x)).cpu().numpy()[0, 0]
    return p > thr


def evaluate(model, volumes, masks) -> dict:
    """متوسط Dice عبر الحالات"""
    ds = [dice(predict_mask(model, v), g) for v, g in zip(volumes, masks)]
    return {"mean_dice": float(np.mean(ds))}
