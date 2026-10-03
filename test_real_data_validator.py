"""D2 FINAL: clinical QC gate guard (8 tests, isolated dirs)."""
from __future__ import annotations

from tools.real_data_validator import CT_SOP, RT_SOP, validate_series


def _write(tmp, n=3, modality="CT", name="", spacing=True, zpos=None,
           contours=False, rescale=True):
    import pydicom
    from pydicom.dataset import FileDataset, FileMetaDataset
    zpos = zpos or [i * 2.0 for i in range(n)]
    for i in range(n):
        meta = FileMetaDataset()
        meta.MediaStorageSOPClassUID = CT_SOP
        meta.TransferSyntaxUID = "1.2.840.10008.1.2"
        ds = FileDataset(str(tmp / f"{i}.dcm"), {}, file_meta=meta,
                         preamble=b"\0" * 128)
        ds.SOPClassUID = CT_SOP
        ds.Modality = modality
        ds.PatientName = name
        ds.ImagePositionPatient = [0, 0, zpos[i]]
        if spacing:
            ds.PixelSpacing = [1.0, 1.0]
        if rescale:
            ds.RescaleIntercept = 0
        ds.save_as(str(tmp / f"{i}.dcm"))
    if contours:
        meta = FileMetaDataset()
        meta.TransferSyntaxUID = "1.2.840.10008.1.2"
        r = FileDataset(str(tmp / "rt.dcm"), {}, file_meta=meta,
                        preamble=b"\0" * 128)
        r.SOPClassUID = RT_SOP
        r.Modality = "RTSTRUCT"
        r.save_as(str(tmp / "rt.dcm"))
    return tmp


def test_valid_accept_with_contours(tmp_path):
    r = validate_series(_write(tmp_path, contours=True))
    assert r["verdict"] == "ACCEPT" and r["has_contours"] and not r["warns"]


def test_wrong_modality_reject(tmp_path):
    assert validate_series(_write(tmp_path, modality="MR"))["verdict"] == "REJECT"


def test_phi_reject(tmp_path):
    r = validate_series(_write(tmp_path, name="DOE^JOHN"))
    assert any("PHI" in x for x in r["rejects"])


def test_duplicate_z_reject(tmp_path):
    r = validate_series(_write(tmp_path, zpos=[0, 0, 4]))
    assert any("duplicate" in x for x in r["rejects"])


def test_nonmonotonic_z_reject(tmp_path):
    r = validate_series(_write(tmp_path, zpos=[0, 4, 2]))
    assert any("non-monotonic" in x for x in r["rejects"])


def test_missing_spacing_reject(tmp_path):
    assert validate_series(_write(tmp_path, spacing=False))["verdict"] == "REJECT"


def test_no_contours_warn_only(tmp_path):
    d = tmp_path / "series"
    d.mkdir()
    _write(d)
    r = validate_series(d)
    assert r["rejects"] == []
    assert r["verdict"] == "ACCEPT"
    assert any("contours" in w for w in r["warns"])


def test_min_slices_reject(tmp_path):
    assert validate_series(_write(tmp_path, n=1), min_slices=2)["verdict"] == "REJECT"
