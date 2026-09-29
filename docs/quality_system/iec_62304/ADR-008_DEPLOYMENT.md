# ADR-008: Deployment strategy (ONNX + hardened container)
Status: ACCEPTED

## Context
Research code must become a deployable, auditable artifact without
touching validated modules.

## Decision
1. Export the trained network to ONNX via a wrapper that replicates
   _to_tensor normalization exactly (ddof=0 variance).
2. Parity proof mandatory: max |torch - onnx| probability difference
   < 1e-4 AND mask agreement == 1.0, recorded in models/MODEL_CARD.json
   with sha256 of both artifacts.
3. Inference contract v1.0: mask + mean_prob; optionally unified
   confidence (ADR-007) + CLIN-001 review flag from live policy.
4. Container: python:3.12-slim, CPU-only pinned torch, non-root user,
   healthcheck; no training inside the image.

## Consequences
- Deployment parity is proven, not assumed.
- Model card is part of the evidence chain (hashes verifiable).
- Clinical flagging travels with the model response.
