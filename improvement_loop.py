"""
ProtonAI - Improvement Loop
حلقة التحسين التكراري: تشخيص أخطاء التحقق/التعميم ← اقتراح تحسينات ← تتبع نسخ
تغلق الدورة البحثية: المنصة تعترف بأخطائها وتتعلم منها منهجياً
أربع تشخيصات: low_accuracy / class_bias / overfitting / weak_generalization
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ProtonAI.ImprovementLoop")


class ImprovementLoop:
    """
    حلقة تحسين.
    - diagnose: يشخّص مشاكل من نتائج التحقق الاستعادي + التعميم الخارجي.
    - record_iteration: يسجّل دورة تحسين برقم نسخة متزايد.
    - history: سجل الدورات.
    """

    def __init__(self, accuracy_threshold: float = 0.8, bias_ratio: float = 0.5):
        if not (0 <= accuracy_threshold <= 1):
            raise ValueError("accuracy_threshold بين 0 و 1")
        if not (0 < bias_ratio <= 1):
            raise ValueError("bias_ratio بين 0 (حصري) و 1")
        self.accuracy_threshold = accuracy_threshold
        self.bias_ratio = bias_ratio
        self.iterations: List[Dict[str, Any]] = []
        self.version = 0

    def diagnose(
        self, retro: Dict[str, Any], external: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """تشخيص المشاكل من النتائج، مرتبة بالأهمية"""
        issues: List[Dict[str, Any]] = []

        # 1) دقة منخفضة
        if retro.get("accuracy", 1.0) < self.accuracy_threshold:
            issues.append({
                "type": "low_accuracy", "severity": "high",
                "suggestion": "ضبط المعاملات الفائقة أو نموذج أقوى",
            })

        # 2) انحياز لصنف (الأخطاء تتركز به)
        errors = retro.get("errors", [])
        if errors:
            counts = Counter(str(e.get("actual")) for e in errors)
            label, cnt = counts.most_common(1)[0]
            if cnt / len(errors) > self.bias_ratio:
                issues.append({
                    "type": "class_bias", "severity": "medium", "label": label,
                    "suggestion": f"إعادة توازن/زيادة عينات الصنف '{label}'",
                })

        # 3+4) تعميم خارجي
        if external is not None:
            if external.get("verdict") == "poor":
                issues.append({
                    "type": "overfitting", "severity": "high",
                    "suggestion": "تنظيم (regularization) أو بيانات أكثر تنوعاً",
                })
            elif not external.get("external_acceptable", True):
                issues.append({
                    "type": "weak_generalization", "severity": "medium",
                    "suggestion": "معايرة خارجية أو تكيّف نطاق (domain adaptation)",
                })

        # ترتيب بالأهمية: high أولاً
        order = {"high": 0, "medium": 1}
        issues.sort(key=lambda i: order.get(i["severity"], 2))
        return issues

    def record_iteration(
        self, issues: List[Dict[str, Any]], chosen: Optional[List[str]] = None
    ) -> int:
        """تسجيل دورة تحسين برقم نسخة متزايد، يرجع النسخة"""
        self.version += 1
        self.iterations.append({
            "version": self.version,
            "issues": list(issues),
            "chosen": list(chosen or []),
            "timestamp": datetime.now().isoformat(),
        })
        logger.info(f"iteration v{self.version}: {len(issues)} مشكلة")
        return self.version

    def history(self) -> List[Dict[str, Any]]:
        """سجل دورات التحسين"""
        return list(self.iterations)
