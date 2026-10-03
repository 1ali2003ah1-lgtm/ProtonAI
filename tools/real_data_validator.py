"""D2 FINAL: clinical-grade pre-intake DICOM QC gate.

Hard rejects: no files, modality!=CT, too few slices, bad spacing, PHI,
duplicate slice z, non-monotonic z. Warns: irregular z-spacing, missing
rescale, missing RT-Struct contours. PHI tags from PARTNERSHIP-MANIFEST.
Returns {verdict, rejects, warns, ...}; optional JSON report for playbook.
"""
from __future__ import annotations

import json
from pathlib import Path

import pydicom

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "partnership" / "PARTNERSHIP-MANIFEST.json"
CT_SOP = "1.2.840.10008.5.1.4.1.1.2"
RT_SOP = "1.2.840.10008.5.1.4.1.1.481.3"


def load_deid_tags():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["deid_tags"]


def _tag(t):
    g, e = t.strip("()").split(",")
    return pydicom.tag.Tag(int(g, 16), int(e, 16))


def _has_phi(ds, t):
    el = ds.get(_tag(t))
    return el is not None and str(el.value).strip() not in ("", "None")


def validate_series(series_dir, min_slices=1):
    files = sorted(Path(series_dir).glob("*.dcm"))
    if not files:
        return {"verdict": "REJECT", "rejects": ["no dicom files"],
                "warns": [], "n_slices": 0}
    ds = [pydicom.dcmread(f, stop_before_pixels=True) for f in files]
    ct = [d for d in ds if str(d.get("SOPClassUID")) == CT_SOP
          or str(d.get("Modality")) == "CT"]
    rt = [d for d in ds if str(d.get("SOPClassUID")) == RT_SOP]
    rejects, warns = [], []

    if not ct or {str(d.get("Modality")) for d in ct} != {"CT"}:
        rejects.append("modality not CT")
    if len(ct) < min_slices:
        rejects.append(f"too few slices {len(ct)}<{min_slices}")
    if ct:
        sp = ct[0].get("PixelSpacing")
        if sp is None or any(float(x) <= 0 for x in sp):
            rejects.append("missing/invalid PixelSpacing")
        if ct[0].get("RescaleIntercept") is None:
            warns.append("missing RescaleIntercept")
        zs = [float(d.ImagePositionPatient[2]) for d in ct
              if d.get("ImagePositionPatient") is not None]
        if zs:
            if len({round(z, 6) for z in zs}) != len(zs):
                rejects.append("duplicate slice z-position")
            if not all(b > a for a, b in zip(zs, zs[1:])):
                rejects.append("non-monotonic slice z")
            diffs = {round(b - a, 4) for a, b in zip(zs, zs[1:])}
            if len(diffs) > 1:
                warns.append(f"irregular z-spacing {sorted(diffs)}")
    phi = [t for t in load_deid_tags() if any(_has_phi(d, t) for d in ct)]
    if phi:
        rejects.append(f"PHI present {phi}")
    if not rt:
        warns.append("no RT-Struct contours (manual gold standard)")

    return {"verdict": "REJECT" if rejects else "ACCEPT",
            "rejects": rejects, "warns": warns, "n_slices": len(ct),
            "has_contours": bool(rt)}


def validate_and_report(series_dir, out, min_slices=1):
    r = validate_series(series_dir, min_slices)
    Path(out).write_text(json.dumps(r, indent=2), encoding="utf-8")
    return r


if __name__ == "__main__":
    import sys
    print(json.dumps(validate_series(sys.argv[1]), indent=2))
