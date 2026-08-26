# Changelog — ProtonAI

جميع التغييرات البارزة موثقة هنا، بترتيب الجلسات (الأحدث أولاً).
التنسيق وفق [Keep a Changelog]؛ الترقيم يعكس نضج المنصة.

## [0.7.0] — جلسة التنظيم (الحالية)
### Added
- docs/architecture.md — خريطة الطبقات السبع وتدفق البيانات.
- clinical_report.py — تقرير الحالة الموحّد (مقاييس + هامش + قرار + أسباب).
- README.md — إعادة كتابة كاملة تعكس المنصة الفعلية.

## [0.6.0] — جاهزية البيانات والتواصل
### Added
- intake_pipeline.py — checksum + chain of custody.
- docs/data_acquisition_plan.md + docs/hospital_request_template.md.
- docs/irb_checklist.md + docs/shadow_mode.md.
- docs/paper_draft.md + docs/paper_stats.py (إحصائيات حية).
- docs/one_pager.md + docs/progress_report.md.

## [0.5.0] — التحقق والمراقبة والتنظيم
### Added
- agreement.py — Cohen's kappa + inter‑observer + Landis‑Koch.
- drift_monitor.py — z‑score + PSI + حالات RAG (post‑market).
- fmea.py + docs/fmea.md — 10 أنماط فشل بـ RPN محسوب.
- samd_classifier.py + docs/samd_roadmap.md — FDA/MDR/IEC 62304.

## [0.4.0] — القرار وتوسعة الأورام
### Added
- safety_gate.py — PROCEED/REVIEW/STOP + human_ack.
- range_margin.py — ميزانية عدم يقين ← هامش مقترح.
- sample_size.py — حاسبة حجم العينة + pilot re‑estimate.
- pstar_validation.py — مقارنة مرجع NIST PSTAR (≤3%).
- tumor_sites.py + site_decision.py — سجل 19 موقعاً + عتبات لكل موقع.
- docs/tumor_expansion.md — خطة الموجات الثلاث.

## [0.3.0] — جاهزية المستشفيات
### Added
- dicom_parser.py — CT/RTSTRUCT/RTDOSE/RTPLAN.
- harmonization.py — توحيد resampling/spacing/intensity + site metadata.
- dry_run_pipeline.py — عرض حي صفر PHI.
- api_main.py — FastAPI CDSS (requires_human_ack).

## [0.2.0] — الدقة العلمية
### Added
- hu_rsp_calibration.py — stoichiometric لكل سكانر + عدم يقين لكل نسيج.
- mc_tissue_compare.py — Monte Carlo عظم/رئة/رخو + WEPL.
- robustness.py — 4D/setup/density + worst‑case + RAG.
- uncertainty_aware.py — ensemble/MC‑Dropout/conformal/ECE.
- seg_metrics.py — Dice/HD95/ASSD.
- segmentation_train.py — سقالة nnU‑Net (GPU).

## [0.1.0] — الأساس الآمن
### Added
- gov_anonymizer.py — إخفاء هوية DICOM (PS3.15 Annex E).
- gov_audit_log.py — سجل append‑only متسلسل بالبصمات.
- config.yaml + config_loader.py — صفر hardcoded.
- docs/data_security.md + docs/statistical_analysis.md.
- CI/CD pipeline (pytest + coverage) — أخضر منذ أول commit.

## [Deferred] — مؤجل (لابتوب / بيانات)
- هيكلة packages (data/ physics/ models/ api/ governance/) — أداة جاهزة.
- DVC + MLflow init.
- تدريب nnU‑Net على GPU.
- dashboard RAG.
- التحقق على بيانات حقيقية (بعد IRB، بعد العطلة).
