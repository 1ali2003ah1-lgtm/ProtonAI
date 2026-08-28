"""
ProtonAI - Dossier Forensics (التحقق من سلامة السجل)
يعيد حساب سلسلة البصمات (hash chain) لـ CaseDossier ويكشف التلاعب:
- expected_hash: نفس معادلة الختم بالـ orchestrator.
- verify_stages: يتحقق تسلسلياً ويرجع أول موضع كسر.
- verify_dossier: واجهة مباشرة على CaseDossier.
لا قرار يُعتمد على dossier غير سليم.
"""

import hashlib
from typing import List, Optional

from case_orchestrator import CaseDossier, Stage

GENESIS = "0" * 64


def expected_hash(prev: str, name: str, status: str, summary: str) -> str:
    return hashlib.sha256(
        (prev + name + status + summary).encode()).hexdigest()


def verify_stages(stages: List[Stage]) -> dict:
    prev = GENESIS
    for i, s in enumerate(stages):
        e = expected_hash(prev, s.name, s.status, s.summary)
        if e != s.hash:
            return {"valid": False, "broken_at": i}
        prev = s.hash
    return {"valid": True, "broken_at": None}


def verify_dossier(dossier: CaseDossier) -> dict:
    return verify_stages(dossier.stages)
