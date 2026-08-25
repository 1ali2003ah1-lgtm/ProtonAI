"""
ProtonAI - Risk: FMEA (Failure Mode & Effects Analysis)
تحليل أنماط الفشل وآثارها لمنصة دعم قرار البروتون.
RPN = Severity × Occurrence × Detection (مقاييس 1-10).
RPN ≥ 100 = إجراء إلزامي؛ RED = إيقاف + مراجعة إجبارية.
"""

FAILURE_MODES = [
    {"id": "FM-01", "name": "خطأ معايرة HU→RSP", "effect": "خطأ مدى/جرعة",
     "S": 9, "O": 3, "D": 4, "control": "hu_rsp_calibration + range_margin"},
    {"id": "FM-02", "name": "تقسيم خاطئ للورم/OAR", "effect": "هدف خاطئ",
     "S": 9, "O": 4, "D": 5, "control": "uncertainty + human review"},
    {"id": "FM-03", "name": "حركة/تنفس غير محسوبة", "effect": "فوات الجرعة",
     "S": 8, "O": 4, "D": 4, "control": "robustness 4D + margins"},
    {"id": "FM-04", "name": "تسرب PHI", "effect": "خرق خصوصية/قانوني",
     "S": 8, "O": 2, "D": 2, "control": "anonymizer PS3.15 + dry-run"},
    {"id": "FM-05", "name": "ثقة زائدة (ECE مرتفع)", "effect": "اعتماد على خطأ",
     "S": 8, "O": 3, "D": 3, "control": "ECE monitoring + human_ack"},
    {"id": "FM-06", "name": "انزياح نطاق (سكانر جديد)", "effect": "تدهور صامت",
     "S": 7, "O": 4, "D": 4, "control": "harmonization + site metadata"},
    {"id": "FM-07", "name": "تعديل سجل التدقيق", "effect": "فقدان مساءلة",
     "S": 6, "O": 1, "D": 1, "control": "append-only hash chain"},
    {"id": "FM-08", "name": "انجراف نموذج صامت", "effect": "تدهور غير ملحوظ",
     "S": 7, "O": 3, "D": 5, "control": "drift monitoring + RAG"},
    {"id": "FM-09", "name": "خطأ إدخال DICOM", "effect": "garbage in",
     "S": 7, "O": 3, "D": 3, "control": "data contracts + dry-run"},
    {"id": "FM-10", "name": "تحيز أتمتة (اعتماد زائد)", "effect": "تجاهل المراجعة",
     "S": 8, "O": 4, "D": 5, "control": "CDSS framing + human_ack"},
]

RPN_ACTION_THRESHOLD = 100


def rpn(fm: dict) -> int:
    return fm["S"] * fm["O"] * fm["D"]


def table() -> list:
    return [{**fm, "RPN": rpn(fm)} for fm in FAILURE_MODES]


def high_risk(threshold: int = RPN_ACTION_THRESHOLD) -> list:
    return [t for t in table() if t["RPN"] >= threshold]
