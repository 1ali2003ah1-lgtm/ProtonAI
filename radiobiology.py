"""
ProtonAI - Radiobiology (RBE متغير + TCP/NTCP)
البروتون ليس RBE ثابت 1.1 دائماً؛ هنا نموذج LQ بـ alpha/beta معتمد على LET:
- variable_rbe: يزداد مع LET ويقل مع الجرعة.
- tcp / ntcp_lkb: منحنيات سيطرة الورم ومضاعفات الأنسجة.
"""

import math

ALPHA_PH = 0.15
AB_PH = 3.0
BETA_PH = ALPHA_PH / AB_PH
K_A, K_B = 0.02, 0.01


def variable_rbe(dose: float, let: float) -> float:
    """RBE نسبي: جرعة فوتون مكافئة / جرعة بروتون"""
    a_p = ALPHA_PH * (1 + K_A * let)
    b_p = BETA_PH * (1 + K_B * let)
    e = a_p * dose + b_p * dose ** 2
    d_ph = (-ALPHA_PH + math.sqrt(ALPHA_PH ** 2 + 4 * BETA_PH * e)) / (2 * BETA_PH)
    return d_ph / dose


def tcp(dose: float, d50: float, gamma50: float = 2.0) -> float:
    """سيطرة الورم اللوجستية"""
    return 1 / (1 + (d50 / dose) ** (4 * gamma50))


def ntcp_lkb(dose: float, td50: float, m: float = 0.1) -> float:
    """مضاعفات النسيج (LKB مبسط)"""
    return 1 / (1 + (td50 / dose) ** (1 / m))
