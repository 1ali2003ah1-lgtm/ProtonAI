# Cybersecurity File — CYBERSECURITY-001

- Threat model: STRIDE (Spoofing, Tampering, Repudiation, Information
  disclosure, DoS, Elevation).
- Controls: token auth (constant-time), rate-limit w/ Retry-After,
  hash-chained audit, DICOM PS3.15 scrubbing, non-root container, TLS at
  reverse proxy, dependency pinning.
- Vulnerability management: advisory monitoring; SBOM via pip freeze;
  critical patches <= 7 days.
- Incident response: revoke/rotate token, freeze imports, audit review.
