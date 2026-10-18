"""XAI Panel: Grad-CAM + Uncertainty with professional visualization.
Designed & developed by: Ali Hussein Thajil"""
from __future__ import annotations
from typing import Optional

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


SIGNATURE = "(c) Ali Hussein Thajil - ProtonAI PRO"


def _add_signature(fig):
    """Add professional signature to figure."""
    fig.text(.99, .01, SIGNATURE, ha="right", fontsize=7,
             color="#666", fontstyle="italic")
    return fig


def _medical_colormap():
    """DICOM-inspired colormap for medical imaging."""
    colors = ["#000000", "#0D47A1", "#1976D2", "#42A5F5",
              "#FFEB3B", "#FF9800", "#F44336", "#B71C1C"]
    return LinearSegmentedColormap.from_list("medical", colors, N=256)


def build_xai_visualization(image_2d: np.ndarray,
                            mask_2d: np.ndarray,
                            uncertainty_map: Optional[np.ndarray] = None,
                            grad_cam: Optional[np.ndarray] = None,
                            title_prefix: str = "") -> Optional[object]:
    """Build professional 3-panel XAI figure.

    Panels:
    1. CT + AI contour (red)
    2. Grad-CAM overlay (explainability)
    3. Uncertainty map (risk assessment)

    Args:
        image_2d: 2D CT slice (HU values)
        mask_2d: Binary segmentation mask
        uncertainty_map: Per-pixel uncertainty (0-1)
        grad_cam: Grad-CAM heatmap (0-1)
        title_prefix: Optional prefix for titles

    Returns:
        matplotlib Figure or None
    """
    if not HAS_MPL:
        return None

    fig, axes = plt.subplots(1, 3, figsize=(15, 5),
                             facecolor="white")

    # Panel 1: CT + Segmentation
    axes[0].imshow(image_2d, cmap="gray", vmin=-1000, vmax=1000)
    if mask_2d is not None and mask_2d.any():
        axes[0].contour(mask_2d, colors="#FF1744", linewidths=1.5,
                        levels=[0.5])
    axes[0].set_title(f"{title_prefix}CT + AI Contour",
                      fontsize=11, fontweight="600",
                      color="#0D47A1", pad=10)
    axes[0].axis("off")
    axes[0].set_aspect("equal")

    # Panel 2: Grad-CAM
    axes[1].imshow(image_2d, cmap="gray", vmin=-1000, vmax=1000)
    if grad_cam is not None and grad_cam.shape == image_2d.shape:
        im = axes[1].imshow(grad_cam, cmap="jet", alpha=0.6,
                            vmin=0, vmax=1)
        cbar = plt.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)
        cbar.set_label("Importance", fontsize=9)
    axes[1].set_title(f"{title_prefix}Grad-CAM (Explainability)",
                      fontsize=11, fontweight="600",
                      color="#0D47A1", pad=10)
    axes[1].axis("off")
    axes[1].set_aspect("equal")

    # Panel 3: Uncertainty
    if uncertainty_map is not None and uncertainty_map.shape == image_2d.shape:
        im = axes[2].imshow(uncertainty_map, cmap=_medical_colormap(),
                            vmin=0, vmax=1)
        cbar = plt.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)
        cbar.set_label("Uncertainty", fontsize=9)
        axes[2].set_title(f"{title_prefix}Uncertainty (Risk)",
                          fontsize=11, fontweight="600",
                          color="#0D47A1", pad=10)
    else:
        axes[2].text(0.5, 0.5, "Uncertainty\nunavailable",
                     ha="center", va="center",
                     fontsize=12, color="#999")
        axes[2].set_title(f"{title_prefix}Uncertainty",
                          fontsize=11, fontweight="600",
                          color="#0D47A1", pad=10)
    axes[2].axis("off")
    axes[2].set_aspect("equal")

    fig.tight_layout(pad=2.0)
    return _add_signature(fig)


def compute_grad_cam_simple(image_2d: np.ndarray,
                            mask_2d: np.ndarray) -> np.ndarray:
    """Simple gradient-based saliency (fallback when no model).

    Computes gradient magnitude as proxy for feature importance.
    """
    gx = np.gradient(image_2d, axis=1)
    gy = np.gradient(image_2d, axis=0)
    magnitude = np.sqrt(gx ** 2 + gy ** 2)

    # Normalize
    if magnitude.max() > 0:
        magnitude = magnitude / magnitude.max()

    # Mask to region of interest
    if mask_2d is not None and mask_2d.any():
        from scipy.ndimage import binary_dilation
        roi = binary_dilation(mask_2d, iterations=3)
        magnitude = magnitude * roi

    return magnitude


def generate_xai_report(image_2d: np.ndarray,
                        mask_2d: np.ndarray,
                        uncertainty_map: Optional[np.ndarray] = None,
                        grad_cam: Optional[np.ndarray] = None) -> dict:
    """Generate XAI analysis report with statistics.

    Returns:
        dict with keys:
        - high_uncertainty_regions: count of pixels with unc > 0.5
        - mean_uncertainty: average uncertainty in target
        - max_uncertainty: peak uncertainty value
        - confidence_score: 1 - mean_uncertainty
    """
    report = {
        "high_uncertainty_regions": 0,
        "mean_uncertainty": 0.0,
        "max_uncertainty": 0.0,
        "confidence_score": 1.0,
    }

    if uncertainty_map is not None:
        report["high_uncertainty_regions"] = int((uncertainty_map > 0.5).sum())
        report["max_uncertainty"] = float(uncertainty_map.max())

        if mask_2d is not None and mask_2d.any():
            target_unc = uncertainty_map[mask_2d > 0.5]
            if len(target_unc) > 0:
                report["mean_uncertainty"] = float(target_unc.mean())
                report["confidence_score"] = 1.0 - report["mean_uncertainty"]

    return report


def format_xai_html(report: dict) -> str:
    """Format XAI report as styled HTML."""
    conf = report["confidence_score"]
    conf_color = "#2E7D32" if conf > 0.8 else "#F9A825" if conf > 0.6 else "#C62828"

    return f"""
<div style="background:#FAFAFA;border-radius:8px;padding:16px;
            border-left:4px solid {conf_color}">
  <h4 style="margin:0 0 12px;color:#0D47A1">XAI Analysis Report</h4>
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td style="padding:6px;color:#666">Confidence Score</td>
      <td style="padding:6px;font-weight:600;color:{conf_color}">
        {conf:.3f}</td>
    </tr>
    <tr>
      <td style="padding:6px;color:#666">Mean Uncertainty (target)</td>
      <td style="padding:6px">{report['mean_uncertainty']:.4f}</td>
    </tr>
    <tr>
      <td style="padding:6px;color:#666">Max Uncertainty</td>
      <td style="padding:6px">{report['max_uncertainty']:.4f}</td>
    </tr>
    <tr>
      <td style="padding:6px;color:#666">High-uncertainty pixels</td>
      <td style="padding:6px">{report['high_uncertainty_regions']:,}</td>
    </tr>
  </table>
  <div style="margin-top:12px;padding:8px;background:#E3F2FD;
              border-radius:4px;font-size:0.85em;color:#0D47A1">
    <b>Interpretation:</b>
    {"High confidence - suitable for clinical use" if conf > 0.8
     else "Moderate confidence - physician review recommended" if conf > 0.6
     else "Low confidence - manual verification required"}
  </div>
</div>
"""
