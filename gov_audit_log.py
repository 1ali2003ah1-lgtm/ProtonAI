"""
ProtonAI - Governance: Append-only Audit Log
سجل تدقيق غير قابل للتعديل: كل إدخال يحمل بصمة SHA256 + بصمة الإدخال السابق
(hash chain) — أي تلاعب بالملف يُكشف فوراً عبر verify()
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("ProtonAI.Governance.AuditLog")

GENESIS = "0" * 64  # بصمة بداية السلسلة


class AuditLog:
    """
    سجل تدقيق متسلسل بالبصمات.
    - log: يضيف عملية (append فقط، لا حذف/تعديل).
    - entries: يقرأ كل العمليات.
    - verify: يعيد حساب السلسلة ويكشف أي تلاعب.
    """

    def __init__(self, path):
        self.path = Path(path)

    def _hash(self, payload) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def entries(self):
        if not self.path.exists():
            return []
        return [json.loads(line) for line in
                self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def log(self, actor: str, action: str, resource: str) -> dict:
        """تسجيل عملية جديدة (append-only) وإرجاع الإدخال"""
        existing = self.entries()
        prev = existing[-1]["hash"] if existing else GENESIS
        payload = {
            "seq": len(existing) + 1,
            "ts": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "resource": resource,
            "prev_hash": prev,
        }
        entry = dict(payload)
        entry["hash"] = self._hash(payload)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"audit #{payload['seq']}: {actor} {action} {resource}")
        return entry

    def verify(self) -> bool:
        """إعادة حساب السلسلة؛ False إذا وُجد أي تلاعب"""
        prev = GENESIS
        for e in self.entries():
            payload = {k: e[k] for k in
                       ["seq", "ts", "actor", "action", "resource", "prev_hash"]}
            if e["prev_hash"] != prev:
                return False
            if self._hash(payload) != e["hash"]:
                return False
            prev = e["hash"]
        return True
