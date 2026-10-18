"""Explainable AI: Grad-CAM for segmentation + uncertainty attribution.
Designed & developed by: Ali Hussein Thajil

FDA/MDR now require explainability for clinical AI. This module provides:
- Grad-CAM: which pixels drove the segmentation
- Uncertainty attribution: which regions are low-confidence
- Combined overlay for physician review
"""
from __future__ import annotations
from typing import Optional, Tuple

import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def _smooth(arr: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(arr, sigma=sigma)


def grad_cam(model, image: np.ndarray, target_layer=None) -> np.ndarray:
    """Compute Grad-CAM heatmap for segmentation model.

    Works with PyTorch CNN models that have a .features or .encoder attribute.
    Falls back to simple input-gradient saliency if no CNN structure found.
    """
    if not HAS_TORCH:
        return input_gradient_saliency(model, image)
    if not hasattr(model, "eval"):
        return input_gradient_saliency(model, image)

    model.eval()
    img_t = torch.from_numpy(image.astype(np.float32))
    if img_t.ndim == 2:
        img_t = img_t.unsqueeze(0).unsqueeze(0)
    img_t = img_t.requires_grad_(True)

    activations, gradients = [], []

    def hook_fwd(mod, inp, out):
        activations.append(out)

    def hook_bwd(mod, grad_in, grad_out):
        gradients.append(grad_out[0])

    target = target_layer
    if target is None:
        for name, mod in model.named_modules():
            if isinstance(mod, (torch.nn.Conv2d,)):
                target = mod
    if target is None:
        return input_gradient_saliency(model, image)

    h1 = target.register_forward_hook(hook_fwd)
    h2 = target.register_full_backward_hook(hook_bwd)
    try:
        out = model(img_t)
        if isinstance(out, tuple):
            out = out[0]
        out_sum = out.sum()
        out_sum.backward()
    finally:
        h1.remove(); h2.remove()

    if not activations or not gradients:
        return input_gradient_saliency(model, image)

    acts = activations[0].detach().cpu().numpy()[0]
    grads = gradients[0].detach().cpu().numpy()[0]
    weights = grads.mean(axis=(1, 2), keepdims=True)
    cam = (weights * acts).sum(axis=0)
    cam = np.maximum(cam, 0)
    if cam.max() > 0:
        cam = cam / cam.max()
    # Resize to input shape
    from scipy.ndimage import zoom
    target_shape = image.shape[-2:]
    cam = zoom(cam, (target_shape[0] / cam.shape[0],
                     target_shape[1] / cam.shape[1]))
    return _smooth(cam)


def input_gradient_saliency(model, image: np.ndarray) -> np.ndarray:
    """Fallback: input-gradient saliency map."""
    if not HAS_TORCH:
        # Simple edge-based saliency
        gx = np.abs(np.diff(image, axis=-1))
        gy = np.abs(np.diff(image, axis=-2))
        gx = gx[..., :-1] if gx.shape[-1] != image.shape[-1] else gx
        gy = gy[..., :-1, :] if gy.shape[-2] != image.shape[-2] else gy
        s = gx[..., :image.shape[-2], :image.shape[-1]] if gx.ndim == 2 else gx
        if s.shape != image.shape:
            s = np.zeros_like(image)
        return s / (s.max() + 1e-9)
    img_t = torch.from_numpy(image.astype(np.float32))
    if img_t.ndim == 2:
        img_t = img_t.unsqueeze(0).unsqueeze(0)
    img_t.requires_grad_(True)
    out = model(img_t)
    if isinstance(out, tuple):
        out = out[0]
    out.sum().backward()
    sal = img_t.grad.abs().detach().cpu().numpy()
    if sal.ndim == 4:
        sal = sal[0, 0]
    sal = sal / (sal.max() + 1e-9)
    return _smooth(sal)


def uncertainty_attribution(uncertainty_map: np.ndarray,
                            segmentation: np.ndarray) -> np.ndarray:
    """Combine uncertainty with segmentation boundary for risk highlighting."""
    from scipy.ndimage import binary_dilation, binary_erosion
    seg = segmentation > 0.5
    if seg.any():
        boundary = seg & ~binary_erosion(seg)
        boundary = binary_dilation(boundary, iterations=2)
    else:
        boundary = np.zeros_like(seg)
    risk = uncertainty_map * (0.5 + 0.5 * boundary.astype(float))
    return risk / (risk.max() + 1e-9)


def explain(model, image: np.ndarray,
            uncertainty_map: Optional[np.ndarray] = None) -> dict:
    """Full explanation bundle: Grad-CAM + uncertainty + risk."""
    cam = grad_cam(model, image)
    out = {"grad_cam": cam, "method": "grad_cam"}
    if uncertainty_map is not None:
        seg_pred = None
        try:
            p = model(torch.from_numpy(image.astype(np.float32))
                      .unsqueeze(0).unsqueeze(0))
            if isinstance(p, tuple):
                p = p[0]
            seg_pred = p.detach().numpy()[0, 0]
        except Exception:
            seg_pred = cam > 0.5
        out["uncertainty"] = uncertainty_map
        out["risk_map"] = uncertainty_attribution(uncertainty_map,
                                                   seg_pred if seg_pred is not None
                                                   else cam)
    return out
