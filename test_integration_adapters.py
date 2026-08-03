"""
ProtonAI - Test Integration Adapters
اختبارات المحوّل FHIR + العقود + الـ Hub
"""

import pytest
from integration_adapters import (
    FHIRMapper, IntegrationAdapter, InMemoryIntegrationAdapter, IntegrationHub,
)
from treatment_plan import TreatmentPlan


def _plan():
    p = TreatmentPlan("p1", "anon_x")
    p.set_section("imaging", {"modality": "CT", "slices": 120})
    p.set_section("physics", {"gamma_pass_rate": 0.97, "coverage_drop": 0.02,
                              "range_in_target": True})  # bool يُتجاوز
    return p


@pytest.fixture
def mapper():
    return FHIRMapper()


class TestFHIRMapper:
    def test_patient_anonymized(self, mapper):
        f = mapper.patient_to_fhir("anon_x")
        assert f.to_dict()["identifier"][0]["value"] == "anon_x"

    def test_bundle_resource_types(self, mapper):
        b = mapper.plan_to_bundle(_plan())
        types = [e["resource"]["resourceType"] for e in b["entry"]]
        assert "Patient" in types
        assert "ImagingStudy" in types
        assert "ServiceRequest" in types
        assert "Observation" in types

    def test_observations_from_float_physics_only(self, mapper):
        b = mapper.plan_to_bundle(_plan())
        obs = [e["resource"] for e in b["entry"]
               if e["resource"]["resourceType"] == "Observation"]
        codes = {o["code"]["text"] for o in obs}
        # gamma + coverage (float) موجودين، range_in_target (bool) متجاوز
        assert "gamma_pass_rate" in codes
        assert "coverage_drop" in codes
        assert "range_in_target" not in codes
        assert len(obs) == 2

    def test_imaging_modality_from_plan(self, mapper):
        b = mapper.plan_to_bundle(_plan())
        st = next(e["resource"] for e in b["entry"]
                  if e["resource"]["resourceType"] == "ImagingStudy")
        assert st["modality"] == "CT"
        assert st["numberOfSeries"] == 120

    def test_subject_references_patient(self, mapper):
        b = mapper.plan_to_bundle(_plan())
        st = next(e["resource"] for e in b["entry"]
                  if e["resource"]["resourceType"] == "ImagingStudy")
        assert st["subject"]["reference"] == "Patient/anon_x"


class TestInMemoryAdapter:
    def test_send_returns_ack_and_stores(self):
        ad = InMemoryIntegrationAdapter("pacs")
        ack = ad.send({"resourceType": "Bundle", "entry": []})
        assert ack.startswith("ack_pacs_")
        assert len(ad.sent) == 1

    def test_fetch_put(self):
        ad = InMemoryIntegrationAdapter()
        ad.put("Patient/p1", {"resourceType": "Patient"})
        assert ad.fetch("Patient/p1")["resourceType"] == "Patient"
        assert ad.fetch("nope") is None

    def test_is_connected(self):
        assert InMemoryIntegrationAdapter().is_connected() is True

    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            IntegrationAdapter()  # type: ignore


class TestIntegrationHub:
    def test_register_and_publish(self):
        hub = IntegrationHub()
        pacs = InMemoryIntegrationAdapter("pacs")
        his = InMemoryIntegrationAdapter("his")
        hub.register(pacs)
        hub.register(his)
        res = hub.publish(_plan())
        assert set(res["acks"].keys()) == {"pacs", "his"}
        assert len(pacs.sent) == 1
        assert len(his.sent) == 1
        # نفس الـ bundle وصل للاثنين
        assert pacs.sent[0] == his.sent[0]

    def test_publish_no_adapters(self):
        hub = IntegrationHub()
        res = hub.publish(_plan())
        assert res["acks"] == {}
        assert res["bundle"]["resourceType"] == "Bundle"

    def test_bundle_has_patient(self):
        hub = IntegrationHub()
        res = hub.publish(_plan())
        types = [e["resource"]["resourceType"] for e in res["bundle"]["entry"]]
        assert "Patient" in types
