"""
ProtonAI - Test DICOM Parser
"""

import pytest

pydicom = pytest.importorskip("pydicom")
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence

from dicom_parser import parse_ct, parse_rtstruct, parse_rtdose, parse_rtplan


def _ct():
    ds = Dataset()
    ds.Modality = "CT"
    ds.Rows = 512
    ds.Columns = 512
    ds.PixelSpacing = [1.0, 1.0]
    ds.SliceThickness = 2.5
    return ds


def _rtstruct():
    ds = Dataset()
    roi = Dataset()
    roi.ROINumber = 1
    roi.ROIName = "GTV"
    oar = Dataset()
    oar.ROINumber = 2
    oar.ROIName = "BRAINSTEM"
    ds.StructureSetROISequence = Sequence([roi, oar])
    return ds


def _rtdose():
    ds = Dataset()
    ds.Rows = 128
    ds.Columns = 128
    ds.DoseGridScaling = 0.01
    ds.GridFrameOffsetVector = [0.0, 2.5, 5.0]
    return ds


def _rtplan():
    ds = Dataset()
    beam = Dataset()
    beam.BeamName = "F1"
    ds.BeamSequence = Sequence([beam])
    ref = Dataset()
    ref.DoseReferenceType = "TARGET"
    ref.TargetPrescribedDose = 70.0
    ds.DoseReferenceSequence = Sequence([ref])
    return ds


class TestCT:
    def test_geometry(self):
        p = parse_ct(_ct())
        assert p["rows"] == 512 and p["columns"] == 512
        assert p["slice_thickness"] == 2.5


class TestRTStruct:
    def test_roi_names(self):
        names = [r["name"] for r in parse_rtstruct(_rtstruct())]
        assert "GTV" in names and "BRAINSTEM" in names


class TestRTDose:
    def test_grid(self):
        p = parse_rtdose(_rtdose())
        assert p["frames"] == 3
        assert p["dose_grid_scaling"] == 0.01


class TestRTPlan:
    def test_beams_and_dose(self):
        p = parse_rtplan(_rtplan())
        assert p["num_beams"] == 1
        assert p["prescribed_dose"] == 70.0
