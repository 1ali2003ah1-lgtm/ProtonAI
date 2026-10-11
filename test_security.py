"""W4 TEAM: clinical security guard (12 tests)."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tools import dicom_import, dicom_scrub, security

ROOT = __import__("pathlib").Path(__file__).resolve().parent
client = TestClient(__import__("server").app)


def test_default_open():
    assert client.get("/api/physics").status_code == 200


def test_auth_401_200():
    s = security.get_settings(); old = s.auth_enabled
    s.auth_enabled = True
    try:
        assert client.get("/api/physics").status_code == 401
        assert client.get("/api/physics",
                          headers={"X-API-Token": s.token}).status_code == 200
    finally:
        s.auth_enabled = old


def test_constant_time_compare():
    t = (ROOT / "tools" / "security.py").read_text(encoding="utf-8")
    assert "hmac.compare_digest" in t


def test_security_headers():
    r = client.get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_rate_limit_retry_after():
    s = security.get_settings(); old = s.rate_limit
    s.rate_limit = 1
    security.get_limiter().reset()
    try:
        client.get("/api/health")
        r = client.get("/api/health")
        assert r.status_code == 429 and "Retry-After" in r.headers
    finally:
        s.rate_limit = old
        security.get_limiter().reset()


def test_audit_chain_valid():
    client.get("/api/health"); client.get("/api/physics")
    assert security.get_audit().verify_chain() is True


def test_audit_no_raw_token():
    s = security.get_settings(); old = s.auth_enabled
    s.auth_enabled = True
    try:
        client.get("/api/physics", headers={"X-API-Token": s.token})
        blob = json.dumps(security.get_audit().entries(), default=str)
        assert s.token not in blob
    finally:
        s.auth_enabled = old


def test_audit_file_written(tmp_path):
    s = security.get_settings(); old = s.audit_file
    s.audit_file = str(tmp_path / "audit.log")
    try:
        client.get("/api/health")
        assert (tmp_path / "audit.log").exists()
    finally:
        s.audit_file = old


def test_scrub_generalize_dates():
    o = dicom_scrub.scrub({"Modality": "CT", "StudyDate": "20260115"},
                          retain_dates=True)
    assert o["StudyDate"] == "20260101"


def test_verify_scrubbed_gate():
    raw = {"PatientName": "X", "Modality": "CT"}
    assert dicom_scrub.verify_scrubbed(raw) is False
    assert dicom_scrub.verify_scrubbed(dicom_scrub.scrub(raw)) is True


def test_import_requires_modality(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"cases": [{"PatientName": "A"}]}))
    with pytest.raises(ValueError):
        dicom_import.import_manifest(p)


def test_import_receipt_sha(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"cases": [{"Modality": "CT"},
                                       {"Modality": "MR"}]}))
    cases, receipt = dicom_import.import_manifest(p)
    assert len(cases) == 2 and len(receipt) == 2
    assert all(len(r["sha256"]) == 64 for r in receipt)
