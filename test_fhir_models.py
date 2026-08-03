"""
ProtonAI - Test FHIR Models
اختبارات نماذج FHIR (to_dict/from_dict + تحقق + bundle)
"""

import math
import pytest
from fhir_models import (
    FHIRPatient, FHIRImagingStudy, FHIRServiceRequest, FHIRObservation,
    make_bundle, reference,
)


class TestReference:
    def test_format(self):
        assert reference("Patient", "p1") == "Patient/p1"


class TestPatient:
    def test_to_dict_resource_type(self):
        p = FHIRPatient("p1", "anon_x")
        d = p.to_dict()
        assert d["resourceType"] == "Patient"
        assert d["id"] == "p1"
        assert d["identifier"][0]["value"] == "anon_x"

    def test_roundtrip(self):
        p = FHIRPatient("p1", "anon_x", gender="female")
        p2 = FHIRPatient.from_dict(p.to_dict())
        assert p2.id == "p1"
        assert p2.identifier_value == "anon_x"
        assert p2.gender == "female"

    def test_gender_optional(self):
        p = FHIRPatient("p1", "a")
        assert "gender" not in p.to_dict()

    def test_invalid_gender_raises(self):
        with pytest.raises(ValueError):
            FHIRPatient("p1", "a", gender="x")

    def test_empty_id_raises(self):
        with pytest.raises(ValueError):
            FHIRPatient("", "a")

    def test_empty_identifier_raises(self):
        with pytest.raises(ValueError):
            FHIRPatient("p1", "   ")


class TestImagingStudy:
    def test_to_dict(self):
        s = FHIRImagingStudy("st1", "p1", modality="CT", number_of_series=3)
        d = s.to_dict()
        assert d["resourceType"] == "ImagingStudy"
        assert d["subject"]["reference"] == "Patient/p1"
        assert d["modality"] == "CT"
        assert d["numberOfSeries"] == 3

    def test_roundtrip(self):
        s = FHIRImagingStudy("st1", "p1")
        s2 = FHIRImagingStudy.from_dict(s.to_dict())
        assert s2.id == "st1"
        assert s2.subject_id == "p1"

    def test_empty_subject_raises(self):
        with pytest.raises(ValueError):
            FHIRImagingStudy("st1", "")


class TestServiceRequest:
    def test_to_dict(self):
        r = FHIRServiceRequest("sr1", "p1")
        d = r.to_dict()
        assert d["resourceType"] == "ServiceRequest"
        assert d["intent"] == "order"
        assert d["status"] == "active"
        assert d["code"]["text"] == "proton_therapy"
        assert d["subject"]["reference"] == "Patient/p1"

    def test_roundtrip(self):
        r = FHIRServiceRequest("sr1", "p1", code_text="bragg")
        r2 = FHIRServiceRequest.from_dict(r.to_dict())
        assert r2.code_text == "bragg"


class TestObservation:
    def test_to_dict_value_quantity(self):
        o = FHIRObservation("o1", "p1", "dose", 2.0, unit="Gy")
        d = o.to_dict()
        assert d["resourceType"] == "Observation"
        assert d["valueQuantity"]["value"] == 2.0
        assert d["valueQuantity"]["unit"] == "Gy"

    def test_roundtrip(self):
        o = FHIRObservation("o1", "p1", "range", 77.0, unit="mm")
        o2 = FHIRObservation.from_dict(o.to_dict())
        assert o2.value == 77.0
        assert o2.unit == "mm"

    def test_nan_raises(self):
        with pytest.raises(ValueError):
            FHIRObservation("o1", "p1", "x", float("nan"))

    def test_inf_raises(self):
        with pytest.raises(ValueError):
            FHIRObservation("o1", "p1", "x", float("inf"))


class TestBundle:
    def test_bundle_structure(self):
        p = FHIRPatient("p1", "a")
        o = FHIRObservation("o1", "p1", "dose", 1.0)
        b = make_bundle([p, o])
        assert b["resourceType"] == "Bundle"
        assert b["type"] == "collection"
        assert len(b["entry"]) == 2
        assert b["entry"][0]["resource"]["resourceType"] == "Patient"
        assert b["entry"][1]["resource"]["resourceType"] == "Observation"

    def test_empty_bundle(self):
        b = make_bundle([])
        assert b["entry"] == []
