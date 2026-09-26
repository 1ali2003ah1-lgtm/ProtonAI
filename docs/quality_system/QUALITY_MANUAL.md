# ProtonAI Quality Manual (ISO 13485:2016)
Doc ID: QM-001 | Version: 1.0 | Status: DRAFT

## 1. Scope
Design, development, verification, validation, release and post-market
surveillance of ProtonAI SaMD.

## 2. QMS processes (cl. 4.4)
Development (IEC 62304), risk (ISO 14971), usability (IEC 62366),
security, document & record control, CAPA, internal audit, management
review, supplier control, training.

## 3. Document & record control (cl. 4.2.4 / 4.2.5)
- Documents live in docs/ with unique IDs and versions.
- Change = pull request; merge = approval record.
- Git history = record retention.

## 4. Management responsibility (cl. 5)
Quality policy: QMS_POLICY.md. Management review inputs: audit results,
CAPA status, risk register changes, post-market data, test metrics.

## 5. Product realization (cl. 7)
Requirements -> risk analysis -> design -> verification -> validation ->
release, with full traceability matrix (TRC-001, to be created).

## 6. Measurement & improvement (cl. 8)
- pytest suite = in-process monitoring (1868 tests baseline).
- drift_monitor = post-market surveillance feed.
- CAPA log: iso_13485/CAPA_LOG.md (to be created).
