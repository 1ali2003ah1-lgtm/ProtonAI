"""
ProtonAI - Test FHIR HTTP Client
اختبارات التكامل الحي (خادم وهمي محلي + عميل HTTP)
"""

import pytest
from fhir_http_client import FHIRClient, start_mock_server, _MockFHIRHandler


@pytest.fixture
def live():
    _MockFHIRHandler.store = {}
    server, url = start_mock_server()
    yield FHIRClient(url)
    server.shutdown()
    server.server_close()


class TestReachability:
    def test_reachable_when_up(self, live):
        assert live.is_reachable() is True

    def test_unreachable_when_down(self):
        # منفذ مغلق → اتصال مرفوض → False
        c = FHIRClient("http://127.0.0.1:1", timeout=1)
        assert c.is_reachable() is False


class TestPostGet:
    def test_post_patient_then_get(self, live):
        status, body = live.post_resource(
            {"resourceType": "Patient", "id": "p1", "gender": "male"})
        assert status == 201
        got = live.get_patient("p1")
        assert got is not None
        assert got["id"] == "p1"
        assert got["gender"] == "male"

    def test_get_missing_returns_none(self, live):
        assert live.get_patient("nope") is None

    def test_post_bundle_created(self, live):
        status, body = live.post_bundle(
            {"resourceType": "Bundle", "id": "b1", "entry": []})
        assert status == 201
        assert body["status"] == "created"

    def test_store_isolated_between_tests(self, live):
        # الـ store يُصفّر بكل fixture → ما يتسرب بين الاختبارات
        assert live.get_patient("p1") is None
