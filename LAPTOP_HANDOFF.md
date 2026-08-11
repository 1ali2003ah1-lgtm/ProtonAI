# LAPTOP_HANDOFF — دليل التسليم والتنفيذ الاحترافي

## 0) الحالة الحالية (منجَز ومختبر، ~1620+ اختبار أخضر)
- المرحلة A (أمان): gov_anonymizer (PS3.15) + gov_audit_log (append-only) + docs/data_security.md + docs/statistical_analysis.md
- المرحلة B (دقة): hu_rsp_calibration + mc_tissue_compare + robustness + uncertainty_aware + seg_metrics
- المرحلة C (مستشفيات): dicom_parser + harmonization
- بنية: config_loader + api_main (FastAPI CDSS) + segmentation_train (سقالة GPU)
- أداة: restructure_for_laptop.py + اختبار خطتها

## 1) أول 30 دقيقة على اللابتوب (بالترتيب)
1. git pull
2. python restructure_for_laptop.py --dry-run   ← شوف الخطة بدون تحريك
3. python restructure_for_laptop.py             ← ينفّز + يشغّل pytest + يرجّع تلقائياً لو فشل
4. git add -A && git commit -m "restructure: packages" && git push
5. pip install dvc mlflow
6. dvc init && git add .dvc .dvcignore && git commit -m "DVC init"

## 2) قواعد الأمان (لا تكسرها)
- اشتغل على فرع refactor/packages أول مرة، والـ CI يحكم.
- أي احمرار = git revert، لا تصلح يدوياً وأنت متعب.
- لا تنقل الـ 90 وحدة القديمة دفعة وحدة؛ وسّع MAPPING تدريجياً وأعد التشغيل.

## 3) القرارات المثبتة (لا تعِد فتحها)
- CDSS فقط؛ القرار النهائي بشري؛ requires_human_ack=True بكل استجابة.
- معايرة HU→RSP لكل سكانر على حدة.
- RED = إيقاف + مراجعة إجبارية، مو لون.
- PyTorch/MONAI للإنتاج؛ Keras baseline للمقارنة.
- لا PHI بالمنصة؛ dry-run على بيانات اصطناعية فقط.

## 4) وش نسوي بعد الهيكلة (تطوير)
- وسّع MAPPING لنقل الوحدات القديمة للحزم تدريجياً.
- فعّل MLflow داخل experiment_tracker (guarded).
- شغّل segmentation_train على GPU ببيانات phantom ثم الحقيقية.
- قس ECE وDice وHD95 وسجّلها بـ MLflow.

## 5) مفاتيح وسياق
- المشرفون: د. حسام يحيى + د. طارق (متاحون الآن، تقييم blinded).
- بيانات حقيقية ~شهر 9 (متعددة المراكز) ← IRB قبل أي استقبال.
- الأهداف: Gamma≥95% @2%/2mm، Dice≥0.85، ECE<0.05.
