# ProtonAI 🧬
## منصة دعم قرار سريري (CDSS) لتحسين دقة العلاج بالبروتون بالذكاء الاصطناعي

> منصة **بحثية** — ليست جهازاً طبياً معتمداً. القرار النهائي **بشري دائماً**.

---

## 🛡️ مبادئ الأمان (غير قابلة للتفاوض)
- **صفر PHI:** لا يدخل المنصة إلا بيانات مُخفية الهوية (DICOM PS3.15 Annex E).
- **RED = إيقاف + مراجعة إجبارية** — مو مجرد لون.
- كل توصية تحمل **عدم يقين** + `requires_human_ack = True`.
- **سجل تدقيق append‑only** متسلسل بالبصمات لكل عملية.

## 🔬 شنو تسوي (الخط الكامل)
DICOM خام ← intake (checksum/custody) ← anonymize ← parse ← harmonize ←
AI (تقسيم + ensemble/conformal/ECE) ← فيزياء (معايرة HU→RSP + مدى + هامش) ←
قرار واعٍ بالموقع (PROCEED/REVIEW/STOP) ← **تقرير سريري موحّد** ← audit.

## 🏗️ البنية (7 طبقات — تفاصيلها بـ docs/architecture.md)
| الطبقة | أبرز الوحدات |
|--------|--------------|
| استلام/بيانات | intake_pipeline، dicom_parser، gov_anonymizer، harmonization، dry_run |
| فيزياء | hu_rsp_calibration، mc_tissue_compare، pstar_validation، gamma_index، range_margin |
| AI | segmentation_train، seg_metrics، uncertainty_aware، explainability، robustness |
| قرار | tumor_sites، site_decision، safety_gate، sample_size، clinical_report |
| تحقق/مراقبة | agreement، drift_monitor، fmea |
| حوكمة | gov_audit_log، config_loader، samd_classifier |
| واجهة | api_main (FastAPI) |

## 🗺️ تغطية الأورام
19 موقعاً بثلاث موجات توسعة؛ المواقع عالية الأولوية (أطفال/CNS/قاعدة جمجمة)
بعتبات أشد: Dice ≥ 0.90 و ECE ≤ 0.03.

## ✅ التحقق وأهداف القبول
- مراجع منشورة: NIST PSTAR (انحراف ≤ 3%) + Gamma ≥ 95% @2%/2mm.
- أهداف: Dice ≥ 0.85 • ECE ≤ 0.05 • inter‑observer kappa ≥ 0.6.
- FMEA محسوب (10 أنماط) + مراقبة drift بعد النشر.
- حالياً على بيانات اصطناعية؛ التحقق السريري بعد IRB ووصول البيانات.

## 📚 الوثائق
architecture • fmea • irb_checklist • shadow_mode • tumor_expansion •
data_acquisition_plan • samd_roadmap • paper_draft • one_pager •
data_security • statistical_analysis.

## 🧪 التشغيل
```bash
pip install -r requirements.txt
pytest -q
```

## 🚧 خارطة الطريق
- ⏸️ لابتوب: هيكلة packages + DVC/MLflow + تدريب nnU‑Net (GPU).
- ⏸️ بعد العطلة: IRB ← استلام بيانات ← دراسة استعادية + shadow mode.

---
*ProtonAI — بحث أكاديمي؛ لا يُستخدم سريرياً قبل التحقق والاعتماد.*
