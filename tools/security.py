"""W4 TEAM: constant-time auth, rate-limit w/ Retry-After, hash-chained audit."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from collections import deque


class Settings:
    def __init__(self):
        self.auth_enabled = os.environ.get("PROTONAI_AUTH", "0") == "1"
        self.token = os.environ.get("PROTONAI_TOKEN", "dev-token")
        self.rate_limit = int(os.environ.get("PROTONAI_RATE_LIMIT", "0"))
        self.rate_window = 60.0
        self.audit_file = os.environ.get("PROTONAI_AUDIT_FILE", "")
        self.hsts = os.environ.get("PROTONAI_HSTS", "0") == "1"

    def token_ok(self, provided):
        return hmac.compare_digest(provided or "", self.token)


_settings = Settings()


def get_settings():
    return _settings


class RateLimiter:
    def __init__(self):
        self._hits = {}

    def allow(self, key):
        s = get_settings()
        if s.rate_limit <= 0:
            return True
        now = time.time()
        q = self._hits.setdefault(key, deque())
        while q and now - q[0] > s.rate_window:
            q.popleft()
        if len(q) >= s.rate_limit:
            return False
        q.append(now)
        return True

    def reset(self):
        self._hits.clear()


_limiter = RateLimiter()


def get_limiter():
    return _limiter


class AuditLog:
    """Tamper-evident: each entry hashes the previous (hash chain)."""

    def __init__(self, maxlen=1000):
        self._d = deque(maxlen=maxlen)
        self._prev = "0" * 64

    def record(self, **kw):
        st = get_settings()
        tok = kw.pop("token", None)
        kw["token_sha"] = hashlib.sha256(tok.encode()).hexdigest()[:8] if tok else None
        kw["ts"] = time.time()
        payload = json.dumps(kw, sort_keys=True, default=str)
        h = hashlib.sha256((self._prev + payload).encode()).hexdigest()
        kw["hash"] = h
        self._prev = h
        self._d.append(kw)
        if st.audit_file:
            with open(st.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(kw, default=str) + "\n")

    def entries(self):
        return list(self._d)

    def verify_chain(self):
        prev = "0" * 64
        for e in self._d:
            kw = {k: v for k, v in e.items() if k != "hash"}
            payload = json.dumps(kw, sort_keys=True, default=str)
            if hashlib.sha256((prev + payload).encode()).hexdigest() != e["hash"]:
                return False
            prev = e["hash"]
        return True


_audit = AuditLog()


def get_audit():
    return _audit
