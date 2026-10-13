# Traceability Matrix — TRACEABILITY-001

| Risk | Control | Verification |
|------|---------|--------------|
| R-01 | physician-in-the-loop + uncertainty map | test_seg_model.py, physics_qa.json |
| R-02 | NTCP display + alert threshold | test_physics.py (robust/V95) |
| R-03 | PS3.15 scrubber + auth + audit | test_security.py |
| R-04 | mandatory-review UI + training | USABILITY-62366-001 |
| R-05 | unit tests + gamma 3%/3mm | test_physics.py (gamma) |
