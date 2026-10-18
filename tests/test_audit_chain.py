"""Audit chain integrity tests."""
import hashlib
import json

import server


def test_chain_links():
    server._audit_chain_last = "GENESIS"
    a1, c1 = server._extend_audit_chain("C1", {"x": 1})
    a2, c2 = server._extend_audit_chain("C2", {"x": 2})
    exp_a1 = hashlib.sha256(
        ("C1:" + json.dumps({"x": 1}, sort_keys=True)).encode()).hexdigest()
    assert a1 == exp_a1
    assert c1 == hashlib.sha256(("GENESIS:" + a1).encode()).hexdigest()
    assert c2 == hashlib.sha256((c1 + ":" + a2).encode()).hexdigest()


def test_hashes_are_64_hex():
    server._audit_chain_last = "GENESIS"
    a, c = server._extend_audit_chain("C9", {"y": 9})
    assert len(a) == 64 and len(c) == 64
