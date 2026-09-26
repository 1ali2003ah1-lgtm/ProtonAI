# Software Development Lifecycle Plan (IEC 62304:2006+A1:2015)
Doc ID: SDL-001 | Version: 2.0 | Status: DRAFT
Applies to: ProtonAI SaMD (all units, zero exceptions)

## 1. Software safety classification
Class C (highest): a defect could contribute to serious injury or death
if external mitigation fails. ProtonAI voluntarily applies Class C
processes to ALL units, safety-related or not.

## 2. Process model with entry/exit criteria
| Phase | Entry criteria | Exit criteria |
|---|---|---|
| Planning | Approved QMS policy | Signed development plan |
| Requirements | Clinical need documented | REQ items reviewed, risk-analyzed, testable |
| Architecture | Approved REQ set | Safety-critical units identified |
| Detailed design | Approved architecture | Traceability established |
| Implementation | Approved design | Code reviewed; static analysis clean |
| Verification | Code complete | Unit+integration green; coverage targets met |
| System testing | Verification report | Gamma/Dice acceptance met |
| Clinical validation | System test report | Clinical evidence dossier accepted |
| Release | Validation complete | Signed release record; risk review; tag |
| Maintenance | Released product | PMS + drift alerts triaged |

## 3. Traceability (cl. 5.1-5.8)
REQ-xxx -> DSG-xxx -> CODE(file/function) -> TST-xxx(pytest node id)
Matrix: iso_13485/TRC-001_TRACEABILITY.md (to be created).

## 4. SOUP management (cl. 5.3.4 / 7.1.2)
See iec_62304/SOUP_REGISTER.md. Every third-party component listed,
pinned, monitored for vulnerabilities.

## 5. Verification & regression policy
- Unit tests mandatory for safety units: safety_gate, dose_engine,
  approval_gates, audit_trails, hu_rsp_calibration, gamma_index.
- Any change to a safety unit triggers FULL-suite regression.
- Warnings are defects: target zero-warning CI.

## 6. Configuration & change management (cl. 8)
Git = CM tool; tags = baselines; branches = features;
pull request + review = change approval record; CHANGELOG.md = history.

## 7. Problem resolution (cl. 9)
Defects = GitHub issues S1-S4; S1/S2 open a CAPA within 48h.

## 8. Release criteria (definition of done)
1) Full pytest green 2) Demos green 3) Risk register reviewed
4) Security scan clean 5) Docs updated 6) Signed tag + release notes.
