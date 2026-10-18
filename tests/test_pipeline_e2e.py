"""End-to-end pipeline tests."""
import tempfile
from pathlib import Path

import numpy as np

from tools import make_report, pipeline, rt_export, train_seg


def _result(seed=0):
    img, _ = train_seg.make_sample(np.random.default_rng(seed))
    return pipeline.run_pipeline(img[None], nz=8)


def test_all_fields():
    r = _result(1)
    for k in ("summary", "masks", "uncertainty", "dose", "dvh", "audit_hash"):
        assert k in r
    assert "physics" in r["summary"]
    assert "disclaimer" in r["summary"]


def test_report_signed_and_big():
    r = _result(2)
    with tempfile.TemporaryDirectory() as td:
        p = make_report.build_report(r, Path(td) / "r.html")
        txt = p.read_text(encoding="utf-8")
        assert "Ali Hussein Thajil" in txt
        assert p.stat().st_size > 2000


def test_rtstruct_2d_and_3d():
    r = _result(3)
    rep = r["rep_slice"]
    with tempfile.TemporaryDirectory() as td:
        a = rt_export.export_rtstruct(r["masks"][rep], Path(td) / "a.dcm")
        m3 = np.zeros((8,) + r["masks"][rep].shape, np.uint8)
        m3[3:6] = r["masks"][rep]
        b = rt_export.export_rtstruct(m3, Path(td) / "b.dcm")
        assert a.stat().st_size > 500 and b.stat().st_size > 500


def test_approval():
    r = _result(4)
    r = pipeline.approve_case(r, "Dr. X", "ok")
    assert r["status"] == "APPROVED"
    assert len(r["approval"]["signature_hash"]) == 64
