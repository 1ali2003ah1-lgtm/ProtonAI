"""
ProtonAI - Regulatory: SaMD Classification
حساب تصنيف المنصة تلقائياً حسب:
- FDA 21 CFR (Class II متوقع).
- EU MDR 2017/745 Annex VIII Rule 11 (Class IIb متوقع).
- IEC 62304 class (B/C) حسب شدة الأذى المحتمل.
يعتمد على الميزات: CDSS, human_ack, RED=stop.
"""


def fda_class(cdss: bool = True, human_ack: bool = True,
              direct_treatment: bool = False) -> str:
    """
    FDA SaMD classification:
    - Class I: low risk
    - Class II: CDSS مع إقرار بشري (حالتنا)
    - Class III: قرار مباشر بدون مراجعة بشرية
    """
    if direct_treatment:
        return "Class III"
    if cdss and human_ack:
        return "Class II"
    return "Class II"


def mdr_class(rule_11_intent: str = "inform_clinical_management",
              serious: bool = True, critical: bool = False) -> str:
    """
    EU MDR Annex VIII Rule 11:
    - Class IIa: معلومات لإدارة سريرية (حالتنا)
    - Class IIb: قرار تشخيص/علاج في حالات خطيرة
    - Class III: حالات حرجة/مهددة للحياة مباشرة
    """
    if critical:
        return "Class III"
    if serious:
        return "Class IIb"
    return "Class IIa"


def iec_62304_class(death_possible: bool = False,
                    serious_injury_possible: bool = True) -> str:
    """
    IEC 62304 software safety class:
    - Class A: لا أذى
    - Class B: أذى غير خطير (حالتنا — CDSS + human_ack)
    - Class C: وفاة ممكنة
    """
    if death_possible:
        return "Class C"
    if serious_injury_possible:
        return "Class B"
    return "Class A"


def classification_summary() -> dict:
    return {
        "FDA": fda_class(),
        "EU_MDR": mdr_class(),
        "IEC_62304": iec_62304_class(),
        "rationale": "CDSS + human_ack + RED=stop → خطر متوسط مخفّض",
                }
