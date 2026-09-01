# ProtonAI — الدليل المعماري

## 1) الرؤية
منصة قرار سريري للعلاج بالبروتون: من بكسل الـ DICOM إلى قرار موثق
بإقرار بشري — سلامة أولاً، وقابلية تدقيق دائماً.

## 2) المبادئ غير القابلة للتفاوض
1. السلامة تعلو: أي RED/STOP يوقف الاعتماد تلقائياً.
2. لا لون وحيد: كل حالة RAG تُعرض بلون+أيقونة+نص (WCAG 2.2 AA).
3. لا قرار بلا تدقيق: كل مرحلة تُختم ببصمة متسلسلة (hash-chain).
4. لا هويات: إخفاء PHI آلي قبل أي معالجة (DICOM PS3.15 + نصوص حرة).
5. الإنسان الأخير: إقرار بشري موثق قبل أي اعتماد.

## 3) الطبقات (من الأسفل للأعلى)
| الطبقة | الوحدات | المسؤولية |
|--------|---------|-----------|
| L0 أساس | safety_gate, site_decision, uncertainty | عتبات وبوابة قرار |
| L1 فيزياء | range_margin, calibration, robustness, radiobiology | دقة فيزيائية |
| L2 سريري | clinical_report, oar_constraints, dose_stats | تقييم الخطة |
| L3 ذكاء | clinical_intelligence, tumor_board | سرد + إجماع |
| L4 حوكمة | orchestrator, forensics, cohort, control_tower | توثيق + مراقبة |
| L5 خصوصية | anonymizer, phi_scrubber, intake_pipeline | استلام آمن |
| L6 عرض | api_enterprise + 4 واجهات | تجربة المستخدم |

## 4) تدفق البيانات
DICOM → Anonymize → AI+Uncertainty → Physics+Margin → Decision Gate
→ Board → Dossier مختوم → Cohort/Governance → Export آمن

## 5) استراتيجية الاختبار
- Unit لكل وحدة • Integration للسلاسل • e2e للـ API والواجهات.
- تغطية ≥90% • اختبارات السلامة 100% (STOP/veto/quorum).

## 6) خارطة الطريق
✅ مكتمل: المحركات، الحوكمة، الواجهات، الخصوصية.
🔜 بعد البيانات: هيكلة packages، DVC+MLflow، nnU‑Net (GPU)،
   تحقق سريري متعدد المراكز.
