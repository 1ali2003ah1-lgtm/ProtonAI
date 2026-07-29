"""
ProtonAI - Normalizers Module
وحدة تطبيع البيانات الاحترافية
تدعم تطبيع الميزات (Features) والجرعات (Doses) والتعامل مع القيم المفقودة
"""

import logging
import math
import statistics
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from copy import deepcopy

logger = logging.getLogger("ProtonAI.Normalizers")


class NormalizationStrategy(str, Enum):
    """استراتيجيات التطبيع المدعومة"""
    MINMAX = "minmax"
    ZSCORE = "zscore"
    MAX_DOSE = "max_dose"  # مخصصة لتطبيع الجرعات الإشعاعية


class MissingValueStrategy(str, Enum):
    """استراتيجيات التعامل مع القيم المفقودة"""
    DROP = "drop"
    MEAN = "mean"
    MEDIAN = "median"
    ZERO = "zero"


class DataNormalizer:
    """
    مقسم البيانات الاحترافي لمنصة ProtonAI.
    يعمل على قوائم القواميس (List of Dicts) ليتوافق مع مخرجات ingestion.py
    """

    def __init__(
        self,
        feature_keys: List[str],
        strategy: NormalizationStrategy = NormalizationStrategy.MINMAX,
        missing_strategy: MissingValueStrategy = MissingValueStrategy.MEAN,
        clip_min: Optional[float] = None,
        clip_max: Optional[float] = None
    ):
        """
        تهيئة المطبع.
        
        Args:
            feature_keys: قائمة بأسماء المفاتيح (الأعمدة) المراد تطبيعها.
            strategy: استراتيجية التطبيع.
            missing_strategy: كيفية التعامل مع القيم المفقودة.
            clip_min: الحد الأدنى للقص (Clipping) بعد التطبيع.
            clip_max: الحد الأقصى للقص (Clipping) بعد التطبيع.
        """
        self.feature_keys = feature_keys
        self.strategy = strategy
        self.missing_strategy = missing_strategy
        self.clip_min = clip_min
        self.clip_max = clip_max
        
        # متغيرات ستُحسب عند استدعاء fit()
        self.stats: Dict[str, Dict[str, float]] = {}
        self.is_fitted = False
        
        logger.info(f"تم تهيئة المطبع للمفاتيح: {feature_keys} باستخدام {strategy.value}")

    def fit(self, data: List[Dict[str, Any]]) -> 'DataNormalizer':
        """
        حساب إحصائيات التطبيع (Min, Max, Mean, Std) من بيانات التدريب.
        """
        if not data:
            raise ValueError("لا يمكن حساب الإحصائيات من بيانات فارغة")

        for key in self.feature_keys:
            # استخراج القيم الرقمية فقط وتجاهل المفقودة (None)
            values = [
                float(row[key]) for row in data 
                if key in row and row[key] is not None and isinstance(row[key], (int, float))
            ]
            
            if not values:
                logger.warning(f"لا توجد قيم صالحة للمفتاح {key}")
                continue

            self.stats[key] = {
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "std": statistics.pstdev(values) if len(values) > 1 else 1.0,
                "median": statistics.median(values)
            }
            
            # منع القسمة على صفر في Z-Score
            if self.stats[key]["std"] == 0:
                self.stats[key]["std"] = 1.0

        self.is_fitted = True
        logger.info(f"تم حساب إحصائيات التطبيع لـ {len(self.stats)} ميزة")
        return self

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        تطبيق التطبيع على البيانات.
        """
        if not self.is_fitted:
            raise RuntimeError("يجب استدعاء fit() قبل transform()")

        normalized_data = deepcopy(data)

        for row in normalized_data:
            for key in self.feature_keys:
                val = row.get(key)
                
                # 1. التعامل مع القيم المفقودة
                if val is None or not isinstance(val, (int, float)):
                    val = self._handle_missing_value(key)
                
                # 2. تطبيق استراتيجية التطبيع
                normalized_val = self._apply_normalization(key, float(val))
                
                # 3. تطبيق القص (Clipping) إذا تم تحديده
                if self.clip_min is not None:
                    normalized_val = max(normalized_val, self.clip_min)
                if self.clip_max is not None:
                    normalized_val = min(normalized_val, self.clip_max)
                
                row[key] = normalized_val

        logger.info(f"تم تطبيع {len(normalized_data)} سجل بنجاح")
        return normalized_data

    def fit_transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """حساب الإحصائيات وتطبيق التطبيع في خطوة واحدة (لبيانات التدريب)"""
        self.fit(data)
        return self.transform(data)

    def _handle_missing_value(self, key: str) -> float:
        """تحديد القيمة البديلة للقيم المفقودة"""
        if self.missing_strategy == MissingValueStrategy.ZERO:
            return 0.0
        elif self.missing_strategy == MissingValueStrategy.MEAN:
            return self.stats.get(key, {}).get("mean", 0.0)
        elif self.missing_strategy == MissingValueStrategy.MEDIAN:
            return self.stats.get(key, {}).get("median", 0.0)
        elif self.missing_strategy == MissingValueStrategy.DROP:
            return 0.0 # سيتم التعامل معها لاحقاً أو إرجاع 0 كقيمة افتراضية آمنة
        return 0.0

    def _apply_normalization(self, key: str, value: float) -> float:
        """تطبيق معادلة التطبيع بناءً على الاستراتيجية"""
        stats = self.stats.get(key)
        if not stats:
            return value

        if self.strategy == NormalizationStrategy.MINMAX:
            min_val = stats["min"]
            max_val = stats["max"]
            if max_val == min_val:
                return 0.0
            return (value - min_val) / (max_val - min_val)
            
        elif self.strategy == NormalizationStrategy.ZSCORE:
            return (value - stats["mean"]) / stats["std"]
            
        elif self.strategy == NormalizationStrategy.MAX_DOSE:
            # تطبيع الجرعة بناءً على أقصى جرعة في مجموعة التدريب
            max_val = stats["max"]
            if max_val == 0:
                return 0.0
            return value / max_val
            
        return value

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """إرجاع الإحصائيات المحسوبة (مفيدة للتقارير)"""
        return self.stats
