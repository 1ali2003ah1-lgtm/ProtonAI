"""
ProtonAI - Board × Intelligence Integration
يدمج قرار مجلس الورم (TumorBoard) بتقرير الذكاء السريري:
- يضيف قسماً للمجلس (قرار/إجماع/نصاب/أقلية/سبب).
- قاعدة سلامة: STOP من المجلس يعلو أي توصية سابقة.
- يحدّث الـ synthesis بمقاييس المجلس للتدقيق والواجهة.
"""

from clinical_intelligence import IntelligenceReport
from tumor_board import BoardRecord


def board_section(board: BoardRecord) -> str:
    """نص قسم المجلس للسرد"""
    lines = [
        f"- القرار: **{board.decision}**",
        f"- الإجماع: {'نعم' if board.consensus else 'لا'} "
        f"({board.agreement_ratio:.0%})",
        f"- النصاب: {'مكتمل' if board.quorum_ok else 'غير مكتمل'}",
    ]
    if board.dissent:
        lines.append(f"- آراء الأقلية الموثقة: {len(board.dissent)}")
    lines.append(f"- السبب: {board.reason}")
    return "\n".join(lines)


def combine(report: IntelligenceReport, board: BoardRecord) -> dict:
    """دمج التقرير + المجلس بمخرَج واحد"""
    overall = ("STOP" if board.decision == "STOP"
               else report.synthesis["overall_quality"])
    narrative = (report.narrative + "\n\n**قرار مجلس الورم:**\n"
                 + board_section(board))
    synthesis = {
        **report.synthesis,
        "overall_quality": overall,
        "board_decision": board.decision,
        "board_consensus": board.consensus,
        "board_agreement": board.agreement_ratio,
        "board_dissent": len(board.dissent),
    }
    return {"narrative": narrative, "synthesis": synthesis,
            "risks": report.risks, "views": report.views}
