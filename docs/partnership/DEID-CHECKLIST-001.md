# DEID-CHECKLIST-001

## Document Control
| ID | Version | Generated | Commit | Status |
|---|---|---|---|---|
| DEID-CHECKLIST-001 | 1.0 | 2026-10-03 | 68cb6af | EFFECTIVE |

## 1. Purpose
Ensure DICOM de-identified before transfer.

## 2. Tags To Scrub
- (0010,0010)
- (0010,0020)
- (0010,0030)
- (0008,0090)
- (0008,0080)

## 3. Verification
Tag dump confirms scrubbed; no PHI in private/free-text; pseudonym
REAL-xxx; provider signs per batch.

## 4. Traceability
DSA-001 s4, HIPAA Safe Harbor, GDPR Art. 4(5), PARTNERSHIP-MANIFEST.
