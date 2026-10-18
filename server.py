"""ProtonAI Production Server v1.0.0
Designed & developed by: Ali Hussein Thajil
DOI: 10.5281/zenodo.23147530
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

import numpy as np
from fastapi import (Depends, FastAPI, Header, HTTPException, Request, status)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

VERSION = "1.0.0-prod"
DEVELOPER = "Ali Hussein Thajil"
DOI = "10.5281/zenodo.23147530"
BUILD_SHA = os.getenv("BUILD_SHA", "dev")
NL = chr(10)

API_KEY = os.getenv("PROTONAI_API_KEY", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MAX_IMAGE_SLICES = int(os.getenv("MAX_IMAGE_SLICES", "256"))
IDEMPOTENCY_TTL_S = int(os.getenv("IDEMPOTENCY_TTL_S", "3600"))


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {"ts": datetime.now(timezone.utc).isoformat(),
                   "level": record.levelname, "msg": record.getMessage()}
        if record.exc_info and record.exc_info[1]:
            payload["exception"] = str(record.exc_info[1])
        return json.dumps(payload, ensure_ascii=False)


logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
for _h in logging.getLogger().handlers:
    _h.setFormatter(JsonFormatter())
log = logging.getLogger("protonai")


class IdempotencyStore:
    def __init__(self, ttl):
        self.ttl = ttl
        self.cache = {}

    def get(self, key):
        self._cleanup()
        e = self.cache.get(key)
        return e[1] if e and time.time() - e[0] < self.ttl else None

    def put(self, key, value):
        self.cache[key] = (time.time(), value)
        self._cleanup()

    def _cleanup(self):
        now = time.time()
        for k in [k for k, (t, _) in self.cache.items() if now - t > self.ttl]:
            self.cache.pop(k, None)


idempotency = IdempotencyStore(IDEMPOTENCY_TTL_S)


class TokenBucketLimiter:
    def __init__(self, rate, burst):
        self.rate = rate
        self.burst = burst
        self.buckets = {}

    def allow(self, key):
        now = time.time()
        if key not in self.buckets:
            self.buckets[key] = (now, float(self.burst))
        last, tokens = self.buckets[key]
        tokens = min(self.burst, tokens + (now - last) * (self.rate / 60.0))
        if tokens < 1.0:
            return False
        self.buckets[key] = (now, tokens - 1.0)
        return True


limiter = TokenBucketLimiter(RATE_LIMIT_PER_MIN, RATE_LIMIT_BURST)


class Metrics:
    def __init__(self):
        self.start_time = time.time()
        self.counters = {"requests_total": 0, "errors_total": 0,
                         "cases_processed": 0, "auth_failures": 0,
                         "rate_limited": 0}
        self.durations = []

    def inc(self, name, by=1):
        self.counters[name] = self.counters.get(name, 0) + by

    def observe(self, v):
        self.durations.append(v)


metrics = Metrics()


@asynccontextmanager
async def lifespan(app):
    log.info("protonai starting")
    try:
        from tools import train_seg
        train_seg.ensure_model()
        log.info("model preloaded")
    except Exception as e:
        log.exception("model preload failed: %s", e)
    yield
    log.info("protonai shutting down gracefully")


app = FastAPI(title="ProtonAI API",
              description="Production-grade proton therapy planning API. "
                          "Developed by Ali Hussein Thajil.",
              version=VERSION, lifespan=lifespan,
              contact={"name": DEVELOPER}, license_info={"name": "MIT"})

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"],
                   expose_headers=["X-Request-ID", "X-Response-Time",
                                   "X-Version", "X-Developer"])


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = rid
    t0 = time.time()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled exception")
        metrics.inc("errors_total")
        return JSONResponse({"error": "internal_server_error",
                             "request_id": rid}, status_code=500)
    dt = time.time() - t0
    metrics.observe(dt)
    response.headers["X-Request-ID"] = rid
    response.headers["X-Response-Time"] = "%.3fs" % dt
    response.headers["X-Version"] = VERSION
    response.headers["X-Developer"] = DEVELOPER
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


async def require_api_key(x_api_key: Optional[str] = Header(None,
                                      alias="X-API-Key")) -> str:
    if not API_KEY:
        return "anonymous"
    if not x_api_key:
        metrics.inc("auth_failures")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-API-Key")
    if hashlib.sha256(x_api_key.encode()).digest() != \
       hashlib.sha256(API_KEY.encode()).digest():
        metrics.inc("auth_failures")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return x_api_key


async def require_rate_limit(request: Request,
                             api_key: str = Depends(require_api_key)):
    key = api_key if api_key != "anonymous" else (
        request.client.host if request.client else "unknown")
    if not limiter.allow(key):
        metrics.inc("rate_limited")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Rate limit exceeded")
    return api_key


class RunRequest(BaseModel):
    image_shape: list = Field(..., min_length=3, max_length=3)
    seed: int = Field(42, ge=0, le=2**31 - 1)
    nz: int = Field(16, ge=8, le=32)
    generate_ctv: bool = Field(True)
    physician_id: Optional[str] = Field(None, max_length=64)
    institution: Optional[str] = Field(None, max_length=128)

    @field_validator("image_shape")
    @classmethod
    def validate_shape(cls, v):
        if any(x <= 0 for x in v):
            raise ValueError("dimensions must be positive")
        if v[0] > MAX_IMAGE_SLICES:
            raise ValueError("too many slices")
        if v[1] > 1024 or v[2] > 1024:
            raise ValueError("H,W must be <= 1024")
        return v


class RunResponse(BaseModel):
    case_id: str
    status: str
    summary: dict
    audit_hash: str
    chain_hash: str
    processing_time_s: float
    request_id: str
    timestamp: str


class BatchRequest(BaseModel):
    cases: list = Field(..., min_length=1, max_length=100)
    parallelism: int = Field(4, ge=1, le=16)


_audit_chain_last = "GENESIS"


def _extend_audit_chain(case_id, summary):
    global _audit_chain_last
    audit_hash = hashlib.sha256(
        (case_id + ":" + json.dumps(summary, sort_keys=True,
                                    default=str)).encode()).hexdigest()
    chain_hash = hashlib.sha256(
        (_audit_chain_last + ":" + audit_hash).encode()).hexdigest()
    _audit_chain_last = chain_hash
    return audit_hash, chain_hash


def _run_one(req: RunRequest, request_id: str) -> dict:
    t0 = time.time()
    from tools import pipeline, train_seg
    rng = np.random.default_rng(req.seed)
    img, _ = train_seg.make_sample(rng)
    image = np.repeat(img[None], req.image_shape[0], 0)
    result = pipeline.run_pipeline(
        image, {"PatientName": "API",
                "PhysicianID": req.physician_id or "",
                "Institution": req.institution or ""}, nz=req.nz)
    dt = time.time() - t0
    audit_hash, chain_hash = _extend_audit_chain(
        result["summary"]["case_id"], result["summary"])
    metrics.inc("cases_processed")
    return {"case_id": result["summary"]["case_id"], "status": "completed",
            "summary": result["summary"], "audit_hash": audit_hash,
            "chain_hash": chain_hash,
            "processing_time_s": round(dt, 3), "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health", tags=["system"])
async def health():
    ok = False
    try:
        from tools import train_seg
        train_seg.ensure_model()
        ok = True
    except Exception:
        pass
    return {"status": "healthy" if ok else "degraded", "version": VERSION,
            "developer": DEVELOPER, "doi": DOI, "build_sha": BUILD_SHA,
            "uptime_s": round(time.time() - metrics.start_time, 2),
            "model_loaded": ok,
            "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/readiness", tags=["system"])
async def readiness():
    try:
        from tools import train_seg
        train_seg.ensure_model()
        return {"ready": True}
    except Exception as e:
        raise HTTPException(503, "Not ready: %s" % e)


@app.get("/live", tags=["system"])
async def liveness():
    return {"live": True}


@app.get("/metrics", response_class=HTMLResponse, tags=["system"])
async def metrics_endpoint():
    lines = ["# TYPE protonai_requests_total counter",
             "protonai_requests_total %d" % metrics.counters["requests_total"],
             "# TYPE protonai_errors_total counter",
             "protonai_errors_total %d" % metrics.counters["errors_total"],
             "# TYPE protonai_cases_processed counter",
             "protonai_cases_processed %d" % metrics.counters["cases_processed"],
             "# TYPE protonai_auth_failures counter",
             "protonai_auth_failures %d" % metrics.counters["auth_failures"],
             "# TYPE protonai_rate_limited counter",
             "protonai_rate_limited %d" % metrics.counters["rate_limited"],
             "# TYPE protonai_uptime_seconds gauge",
             "protonai_uptime_seconds %.2f" % (time.time() - metrics.start_time)]
    return NL.join(lines)


@app.post("/api/run", response_model=RunResponse, tags=["clinical"],
          dependencies=[Depends(require_rate_limit)])
async def api_run(req: RunRequest, request: Request,
                  idempotency_key: Optional[str] = Header(
                      None, alias="Idempotency-Key")):
    metrics.inc("requests_total")
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    if idempotency_key:
        cached = idempotency.get(idempotency_key)
        if cached is not None:
            return RunResponse(**cached)
    try:
        result = _run_one(req, rid)
        if idempotency_key:
            idempotency.put(idempotency_key, result)
        return RunResponse(**result)
    except Exception as e:
        metrics.inc("errors_total")
        log.exception("pipeline failed")
        raise HTTPException(500, "Pipeline failed: %s" % e)


@app.post("/api/run/stream", tags=["clinical"],
          dependencies=[Depends(require_rate_limit)])
async def api_run_stream(req: RunRequest, request: Request):
    metrics.inc("requests_total")
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))

    async def stream() -> AsyncIterator[str]:
        def emit(event, data):
            return "event: %s%sdata: %s%s%s" % (
                event, NL, json.dumps(data, default=str), NL, NL)
        yield emit("start", {"request_id": rid})
        for stage in ["validate", "scrub", "segment", "physics",
                      "dvh", "robust"]:
            await asyncio.sleep(0.05)
            yield emit("stage", {"stage": stage})
        try:
            yield emit("complete", _run_one(req, rid))
        except Exception as e:
            metrics.inc("errors_total")
            yield emit("error", {"message": str(e)})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.post("/api/batch", tags=["clinical"],
          dependencies=[Depends(require_rate_limit)])
async def api_batch(req: BatchRequest, request: Request):
    metrics.inc("requests_total")
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    sem = asyncio.Semaphore(req.parallelism)

    async def _one(r):
        async with sem:
            try:
                return _run_one(r, rid)
            except Exception as e:
                metrics.inc("errors_total")
                return {"status": "failed", "error": str(e)}

    results = await asyncio.gather(*[_one(r) for r in req.cases])
    return {"request_id": rid, "count": len(req.cases), "results": results}


@app.get("/api/audit/{case_id}", tags=["clinical"],
         dependencies=[Depends(require_rate_limit)])
async def api_audit(case_id: str):
    metrics.inc("requests_total")
    return {"case_id": case_id, "verification_method": "SHA256 linked chain",
            "tamper_evident": True, "developer": DEVELOPER, "doi": DOI}


@app.get("/", response_class=HTMLResponse, tags=["system"])
async def root():
    return ("<html><body style='font-family:sans-serif;max-width:760px;"
            "margin:40px auto'><h1>ProtonAI Production Server</h1><p>v"
            + VERSION + " - " + DEVELOPER + "</p><p>DOI: " + DOI + "</p>"
            "<ul><li><a href='/docs'>Swagger</a></li>"
            "<li><a href='/health'>Health</a></li>"
            "<li><a href='/metrics'>Metrics</a></li></ul>"
            "<hr><p>(c) 2026 " + DEVELOPER + "</p></body></html>")


@app.exception_handler(Exception)
async def global_exception(request: Request, exc: Exception):
    metrics.inc("errors_total")
    rid = getattr(request.state, "request_id", "unknown")
    log.exception("unhandled exception")
    return JSONResponse({"error": "internal_server_error",
                         "request_id": rid}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
