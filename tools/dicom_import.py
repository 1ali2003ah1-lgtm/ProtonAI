"""W4 TEAM: validating importer with per-case sha256 receipt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.dicom_scrub import scrub, verify_scrubbed

REQUIRED = {"Modality"}


def build_receipt(cases):
    return [{"index": i,
             "sha256": hashlib.sha256(
                 json.dumps(c, sort_keys=True, default=str).encode()
             ).hexdigest()} for i, c in enumerate(cases)]


def import_manifest(path, retain_dates=False):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = []
    for c in data["cases"]:
        missing = REQUIRED - set(c)
        if missing:
            raise ValueError(f"missing required clinical tags: {missing}")
        sc = scrub(c, retain_dates=retain_dates)
        if not verify_scrubbed(sc):
            raise ValueError("PHI remains after scrub")
        cases.append(sc)
    return cases, build_receipt(cases)


def dicomweb_fetch(base, study_uid, token=None):
    import httpx
    headers = {"Accept": "application/dicom+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = httpx.get(f"{base}/studies/{study_uid}", headers=headers, timeout=10)
    r.raise_for_status()
    payload = r.json()
    return scrub(payload[0] if isinstance(payload, list) else payload)
