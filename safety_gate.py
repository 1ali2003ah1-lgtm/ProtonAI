"""
ProtonAI - Safety Gate (CDSS)
بوابة قرار موحّدة: تدمج مؤشرات الجودة وتطلع قراراً آمناً:
- STOP: حالة RED (إيقاف ومراجعة إجبارية).
- REVIEW: أي مؤشر خارج الهدف (Dice/ECE/AMBER).
- PROCEED: كل شي ضمن الأهداف.
كل قرار يحمل requires_human_ack=True (القرار النهائي بشري).
"""

from config_loader import load_config, get


def evaluate(status: str = "GREEN", dice: float = 0.95,
             ece: float = 0.02, uncertainty: float = 0.1) -> dict:
    """تقييم موحّد يرجع قرار + أسباب + إقرار بشري إجباري"""
    cfg = load_config()
    dice_t = get(cfg, "ai", "dice_target", default=0.85)
    ece_t = get(cfg, "ai", "ece_target", default=0.05)

    stop, review = [], []
    if status == "RED":
        stop.append("حالة RED: إيقاف ومراجعة إجبارية")
    if status == "AMBER":
        review.append("حالة AMBER: مراجعة مستحسنة")
    if dice < dice_t:
        review.append(f"Dice ({dice:.2f}) أقل من الهدف ({dice_t})")
    if ece > ece_t:
        review.append(f"ECE ({ece:.2f}) أعلى من الهدف ({ece_t})")

    decision = "STOP" if stop else ("REVIEW" if review else "PROCEED")
    return {"decision": decision, "reasons": stop + review,
            "requires_human_ack": True}
