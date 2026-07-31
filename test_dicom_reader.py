"""
ProtonAI - Test DICOM Reader
اختبارات بوابة DICOM (تنشئ ملف DICOM وهمي صالح، لا تحتاج بيانات حقيقية)
"""

import numpy as np
import pytest

# حماية مزدوجة: لو pydicom مو مثبت، الاختبار يُتخطى بأدب (build يبقى أخضر)
pydicom = pytest.importorskip("pydicom")

from dicom_reader import DicomReader, _load_pydicom


def _make_dummy_dicom(path, patient_id="P1", rows=4, cols=4,
                      slope=1.0, intercept=-1024.0):
    """إنشاء ملف DICOM CT وهمي صالح للاختبار"""
    file_meta = pydicom.Dataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    ds = pydicom.FileDataset(
        str(path), {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.PatientID = patient_id
    ds.Modality = "CT"
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.RescaleSlope = slope
    ds.RescaleIntercept = intercept
    arr = np.arange(rows * cols, dtype=np.int16).reshape(rows, cols)
    ds.PixelData = arr.tobytes()
    try:  # متانة عبر إصدارات pydicom المختلفة
        ds.is_little_endian = True
        ds.is_implicit_VR = False
    except Exception:
        pass
    ds.save_as(str(path))
    return ds


@pytest.fixture
def dicom_file(tmp_path):
    p = tmp_path / "dummy.dcm"
    _make_dummy_dicom(p)
    return p


class TestLoadPydicom:
    def test_returns_module(self):
        mod = _load_pydicom()
        assert hasattr(mod, "dcmread")


class TestIsDicom:
    def test_valid(self, dicom_file):
        assert DicomReader().is_dicom(dicom_file) is True

    def test_invalid(self, tmp_path):
        bad = tmp_path / "not_dicom.txt"
        bad.write_text("hello", encoding="utf-8")
        assert DicomReader().is_dicom(bad) is False


class TestReadMetadata:
    def test_patient_id(self, dicom_file):
        assert DicomReader().read_metadata(dicom_file)["PatientID"] == "P1"

    def test_modality(self, dicom_file):
        assert DicomReader().read_metadata(dicom_file)["Modality"] == "CT"

    def test_missing_key_is_none(self, dicom_file):
        assert DicomReader().read_metadata(dicom_file)["PatientName"] is None

    def test_path_stored(self, dicom_file):
        assert DicomReader().read_metadata(dicom_file)["_path"].endswith("dummy.dcm")

    def test_custom_keys(self, dicom_file):
        meta = DicomReader(metadata_keys=["Modality"]).read_metadata(dicom_file)
        assert "Modality" in meta

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            DicomReader().read_metadata(tmp_path / "nope.dcm")


class TestReadPixels:
    def test_shape(self, dicom_file):
        assert DicomReader().read_pixels(dicom_file).shape == (4, 4)

    def test_dtype_float(self, dicom_file):
        assert DicomReader().read_pixels(dicom_file).dtype == float

    def test_rescale_applied_to_hu(self, dicom_file):
        px = DicomReader().read_pixels(dicom_file, apply_rescale=True)
        assert px.min() == pytest.approx(-1024.0)
        assert px.max() == pytest.approx(15.0 - 1024.0)

    def test_no_rescale_raw(self, dicom_file):
        px = DicomReader().read_pixels(dicom_file, apply_rescale=False)
        assert px.min() == pytest.approx(0.0)
        assert px.max() == pytest.approx(15.0)


class TestRead:
    def test_full_keys(self, dicom_file):
        r = DicomReader().read(dicom_file)
        assert {"metadata", "pixels", "shape", "min", "max"} <= set(r)
        assert r["shape"] == [4, 4]

    def test_min_max_consistent(self, dicom_file):
        r = DicomReader().read(dicom_file)
        assert r["min"] == pytest.approx(float(r["pixels"].min()))
        assert r["max"] == pytest.approx(float(r["pixels"].max()))
