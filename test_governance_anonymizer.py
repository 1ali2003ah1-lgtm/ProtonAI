"""
ProtonAI - Test Governance Anonymizer
"""

import pytest

pydicom = pytest.importorskip("pydicom")
from pydicom.dataset import Dataset

from governance.anonymizer import deidentify, is_deidentified, PHI_TAGS


def _patient():
    ds = Dataset()
    ds.PatientName = "ALI AHMED"
    ds.PatientID = "123456"
    ds.PatientBirthDate = "20000101"
    ds.InstitutionName = "BAGHDAD HOSPITAL"
    ds.ReferringPhysicianName = "DR X"
    return ds


class TestDeidentify:
    def test_phi_removed(self):
        ds = deidentify(_patient(), "P-001")
        assert ds.PatientBirthDate == ""
        assert ds.InstitutionName == ""
        assert ds.ReferringPhysicianName == ""

    def test_pseudonym_applied(self):
        ds = deidentify(_patient(), "P-001")
        assert ds.PatientID == "P-001"
        assert ds.PatientName == "P-001"

    def test_marked_deidentified(self):
        ds = deidentify(_patient(), "P-001")
        assert ds.PatientIdentityRemoved == "YES"
        assert "PS3.15" in ds.DeidentificationMethod

    def test_is_deidentified_true(self):
        assert is_deidentified(deidentify(_patient(), "P-001")) is True


class TestNotDeidentified:
    def test_raw_patient_fails(self):
        assert is_deidentified(_patient()) is False

    def test_partial_fails(self):
        ds = deidentify(_patient(), "P-002")
        ds.PatientBirthDate = "19990101"  # تسرب PHI بعد الإخفاء
        assert is_deidentified(ds) is False


class TestTagsConstant:
    def test_phi_tags_present(self):
        assert "PatientName" in PHI_TAGS
        assert "PatientBirthDate" in PHI_TAGS
