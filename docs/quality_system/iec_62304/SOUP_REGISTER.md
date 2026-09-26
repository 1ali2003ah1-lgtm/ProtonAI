# SOUP Register (IEC 62304 cl. 7.1.2 / 5.3.4)
Doc ID: SDL-002 | Version: 1.0 | LIVING DOCUMENT
SOUP = Software of Unknown Provenance (third-party components).

| ID | Component | Version | Function in SaMD | Safety relevance | Monitoring |
|---|---|---|---|---|---|
| SOUP-01 | Python | 3.14.x | Runtime | High | Patch releases monthly |
| SOUP-02 | PyTorch | 2.14.0+cpu | Segmentation train/inference | High (R-001) | CVE feed + pinned |
| SOUP-03 | numpy | per requirements | Array math | High | pinned |
| SOUP-04 | pydicom | per requirements | DICOM I/O | High (R-004) | pinned + PHI tests |
| SOUP-05 | scikit-learn | per requirements | Metrics/eval | Medium | pinned |
| SOUP-06 | Streamlit | 1.64.0 | Clinical UI | Medium (R-006) | pinned |
| SOUP-07 | pytest | 9.x | Verification tooling | Indirect | pinned |

Rules:
- Versions pinned in requirements.txt; upgrades require regression +
  risk review + CHANGELOG entry.
- Known vulnerabilities triaged within 7 days; S1 fixes within 30 days.
- Anomalous SOUP behaviour in a safety path = incident + CAPA.
