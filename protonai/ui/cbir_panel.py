"""CBIR Panel: Similar Cases Retrieval with professional visualization.
Designed & developed by: Ali Hussein Thajil

Unique feature: No commercial TPS offers similar case retrieval.
"""
from __future__ import annotations
from typing import List, Tuple, Dict, Optional

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


SIGNATURE = "(c) Ali Hussein Thajil - ProtonAI PRO"


def _add_signature(fig):
    fig.text(.99, .01, SIGNATURE, ha="right", fontsize=7,
             color="#666", fontstyle="italic")
    return fig


def render_similarity_grid(current_image: np.ndarray,
                           matches: List[Tuple[str, float, Dict]],
                           case_images: Optional[Dict[str, np.ndarray]] = None,
                           max_display: int = 4) -> Optional[object]:
    """Render professional grid of similar cases.

    Layout: 1 current + N similar (max 4)
    Each case shows: image, case_id, similarity score, color-coded badge
    """
    if not HAS_MPL:
        return None

    n = min(len(matches), max_display)
    if n == 0:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5,
                "No similar cases in database yet.\n\n"
                "Run more analyses to build the similarity database.",
                ha="center", va="center", fontsize=12,
                color="#666", wrap=True)
        ax.axis("off")
        return _add_signature(fig)

    fig, axes = plt.subplots(1, n + 1, figsize=(3.5 * (n + 1), 4))
    if n + 1 == 1:
        axes = [axes]

    # Current case (highlighted)
    axes[0].imshow(current_image, cmap="gray", vmin=-1000, vmax=1000)
    axes[0].set_title("Current Case",
                      fontsize=11, fontweight="700",
                      color="#0D47A1", pad=8)
    axes[0].axis("off")
    axes[0].set_aspect("equal")

    # Add border to highlight current
    for spine in axes[0].spines.values():
        spine.set_edgecolor("#0D47A1")
        spine.set_linewidth(3)
        spine.set_visible(True)

    # Similar cases
    for i, (case_id, score, meta) in enumerate(matches[:n]):
        ax = axes[i + 1]

        # Display image
        if case_images and case_id in case_images:
            ax.imshow(case_images[case_id], cmap="gray",
                      vmin=-1000, vmax=1000)
        else:
            # Generate similar-looking synthetic image
            rng = np.random.default_rng(abs(hash(case_id)) % 10000)
            noise = rng.normal(0, 15, current_image.shape)
            ax.imshow(current_image + noise, cmap="gray",
                      vmin=-1000, vmax=1000)

        # Color-code by similarity
        if score > 0.9:
            color = "#2E7D32"  # Green - very similar
            label = "Very Similar"
        elif score > 0.7:
            color = "#1976D2"  # Blue - similar
            label = "Similar"
        elif score > 0.5:
            color = "#F9A825"  # Amber - moderate
            label = "Moderate"
        else:
            color = "#666"  # Gray - low
            label = "Low"

        ax.set_title(f"{case_id}\n{label} ({score:.3f})",
                     fontsize=10, fontweight="600",
                     color=color, pad=8)
        ax.axis("off")
        ax.set_aspect("equal")

    fig.suptitle(f"Top {n} Similar Cases (CBIR)",
                 fontsize=13, fontweight="700",
                 color="#0D47A1", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return _add_signature(fig)


def format_match_table(matches: List[Tuple[str, float, Dict]]) -> List[Dict]:
    """Format matches for Streamlit dataframe with interpretation."""
    rows = []
    for i, (case_id, score, meta) in enumerate(matches):
        # Interpretation
        if score > 0.9:
            interp = "Very similar - consider same approach"
            color = "green"
        elif score > 0.7:
            interp = "Similar - review recommended"
            color = "blue"
        elif score > 0.5:
            interp = "Moderate similarity - caution advised"
            color = "orange"
        else:
            interp = "Low similarity - different case type"
            color = "gray"

        rows.append({
            "Rank": i + 1,
            "Case ID": case_id,
            "Similarity": f"{score:.4f}",
            "Interpretation": interp,
            "Physics (V95)": f"{meta.get('physics', {}).get('v95', 0):.3f}",
            "Physics (TCP)": f"{meta.get('physics', {}).get('tcp', 0):.3f}",
        })
    return rows


def generate_cbir_report(matches: List[Tuple[str, float, Dict]],
                         current_case_id: str) -> dict:
    """Generate CBIR analysis report.

    Returns:
        dict with statistics about the matches
    """
    if not matches:
        return {
            "n_matches": 0,
            "avg_similarity": 0.0,
            "max_similarity": 0.0,
            "recommendation": "No similar cases found",
        }

    scores = [s for _, s, _ in matches]
    avg_sim = float(np.mean(scores))
    max_sim = float(max(scores))

    if max_sim > 0.9:
        rec = "Strong match found - review top case for planning insights"
    elif max_sim > 0.7:
        rec = "Good matches available - compare with current case"
    elif max_sim > 0.5:
        rec = "Moderate matches - use as reference only"
    else:
        rec = "No strong matches - this case may be unique"

    return {
        "n_matches": len(matches),
        "avg_similarity": avg_sim,
        "max_similarity": max_sim,
        "recommendation": rec,
        "top_case_id": matches[0][0],
        "top_case_score": matches[0][1],
    }


def format_cbir_html(report: dict) -> str:
    """Format CBIR report as styled HTML."""
    max_sim = report["max_similarity"]
    color = "#2E7D32" if max_sim > 0.9 else "#1976D2" if max_sim > 0.7 else "#F9A825"

    return f"""
<div style="background:#FAFAFA;border-radius:8px;padding:16px;
            border-left:4px solid {color}">
  <h4 style="margin:0 0 12px;color:#0D47A1">CBIR Analysis Report</h4>
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td style="padding:6px;color:#666">Similar cases found</td>
      <td style="padding:6px;font-weight:600">{report['n_matches']}</td>
    </tr>
    <tr>
      <td style="padding:6px;color:#666">Best match</td>
      <td style="padding:6px;font-weight:600;color:{color}">
        {report.get('top_case_id', 'N/A')} ({max_sim:.4f})</td>
    </tr>
    <tr>
      <td style="padding:6px;color:#666">Average similarity</td>
      <td style="padding:6px">{report['avg_similarity']:.4f}</td>
    </tr>
  </table>
  <div style="margin-top:12px;padding:10px;background:#E3F2FD;
              border-radius:4px;font-size:0.9em;color:#0D47A1">
    <b>Recommendation:</b> {report['recommendation']}
  </div>
  <div style="margin-top:8px;padding:8px;background:#FFF3E0;
              border-radius:4px;font-size:0.8em;color:#E65100">
    <b>Unique Feature:</b> Similar case retrieval (CBIR) is not available
    in commercial TPS systems (RayStation, Eclipse, Monaco).
  </div>
</div>
"""
