# Threat Model & Security Architecture (STRIDE) - ProtonAI
Doc ID: SEC-001 | Version: 2.0 | Status: DRAFT

## 1. Assets
A1 Patient DICOM/PHI | A2 Model weights & configs | A3 Treatment plans |
A4 Audit logs | A5 Credentials & sessions | A6 Review signatures

## 2. STRIDE analysis
| ID | Threat | STRIDE | Asset | Existing control | Gap / planned |
|---|---|---|---|---|---|
| T-01 | DICOM interception in transit | I | A1 | TLS-only policy | Enforce in api_main |
| T-02 | PHI remnants in exports/logs | I | A1 | phi_scrubber + anonymizer + tests | Expand to dashboards |
| T-03 | Model weight tampering | T | A2 | none yet | Hash+signature verify at load |
| T-04 | Privilege escalation UI/API | E | A3,A6 | access_control RBAC | Session audit + rate limits |
| T-05 | Audit log rewrite/deletion | R | A4 | append-only intent | Hash-chain (Merkle) log |
| T-06 | Repudiation of approvals | R | A6 | approval_gates | Crypto-signed approvals |
| T-07 | DoS on planning service | D | availability | none yet | Quotas + rate limits |
| T-08 | Secret leakage in repo | I | A5 | .gitignore | Pre-commit secret scan in CI |
| T-09 | Spoofed user/session | S | A5 | RBAC roles | MFA for approver roles |

## 3. Standing security rules
No secrets in repo; dependency scan in CI; S1 patch <=30 days;
least privilege; every access audited; secure-by-default configs.

## 4. Incident response (draft)
Detect -> Contain (safety_gate deny-all kill switch) -> Assess vs
RSK-001 -> Notify per regulator timelines -> CAPA -> public post-mortem
when patient safety involved.
