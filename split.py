"""
ProtonAI - Data Splitting Module
وحدة تقسيم البيانات الاحترافية
تدعم التقسيم العشوائي، الطبقي (Stratified)، والتسلسلي (Temporal)
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum

logger = logging.getLogger("ProtonAI.Splitter")


class SplitStrategy(str, Enum):
    """استراتيجيات التقسيم المدعومة"""
    RANDOM = "random"
    STRATIFIED = "stratified"
    TEMPORAL = "temporal"


class DataSplitter:
    """
    مقسم البيانات الاحترافي لمنصة ProtonAI.
    يضمن التكرارية (Reproducibility) عبر تثبيت البذرة العشوائية.
    """

    def __init__(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        strategy: SplitStrategy = SplitStrategy.RANDOM,
        stratify_key: Optional[str] = None,
        date_key: Optional[str] = None
    ):
        """
        تهيئة مقسم البيانات.
        
        Args:
            train_ratio: نسبة بيانات التدريب (افتراضي 70%)
            val_ratio: نسبة بيانات التحقق (افتراضي 15%)
            test_ratio: نسبة بيانات الاختبار (افتراضي 15%)
            random_seed: البذرة العشوائية لضمان التكرار
            strategy: استراتيجية التقسيم
            stratify_key: مفتاح التقسيم الطبقي (مثل نوع الورم)
            date_key: مفتاح التاريخ للتقسيم التسلسلي
        """
        # التحقق من أن النسب صحيحة
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"مجموع النسب يجب أن يساوي 1.0، المجموع الحالي: {total}"
            )
        
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.strategy = strategy
        self.stratify_key = stratify_key
        self.date_key = date_key
        
        logger.info(
            f"تم تهيئة المقسم: train={train_ratio}, val={val_ratio}, "
            f"test={test_ratio}, strategy={strategy.value}"
        )

    def split(
        self, 
        data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        تقسيم البيانات إلى ثلاث مجموعات.
        
        Args:
            data: قائمة من القواميس تمثل بيانات المرضى
            
        Returns:
            Tuple تحتوي على (train_data, val_data, test_data)
        """
        if not data:
            raise ValueError("قائمة البيانات فارغة!")
        
        if len(data) < 10:
            logger.warning(f"عدد العينات قليل ({len(data)})، قد لا يكون التقسيم ممثلاً")

        # اختيار الاستراتيجية
        if self.strategy == SplitStrategy.RANDOM:
            return self._random_split(data)
        elif self.strategy == SplitStrategy.STRATIFIED:
            return self._stratified_split(data)
        elif self.strategy == SplitStrategy.TEMPORAL:
            return self._temporal_split(data)
        else:
            raise ValueError(f"استراتيجية غير معروفة: {self.strategy}")

    def _random_split(
        self, 
        data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """التقسيم العشوائي البسيط"""
        import random
        
        # إنشاء نسخة من البيانات
        data_copy = data.copy()
        
        # تثبيت البذرة العشوائية للتكرار
        random.seed(self.random_seed)
        
        # خلط البيانات
        random.shuffle(data_copy)
        
        # حساب الأحجام
        n = len(data_copy)
        train_size = int(n * self.train_ratio)
        val_size = int(n * self.val_ratio)
        
        # التقسيم
        train_data = data_copy[:train_size]
        val_data = data_copy[train_size:train_size + val_size]
        test_data = data_copy[train_size + val_size:]
        
        logger.info(
            f"تم التقسيم العشوائي: train={len(train_data)}, "
            f"val={len(val_data)}, test={len(test_data)}"
        )
        
        return train_data, val_data, test_data

    def _stratified_split(
        self, 
        data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """التقسيم الطبقي - يحافظ على توزيع الفئات"""
        if not self.stratify_key:
            raise ValueError("يجب تحديد stratify_key للتقسيم الطبقي")
        
        # تجميع البيانات حسب الفئة
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in data:
            key = str(item.get(self.stratify_key, "unknown"))
            groups.setdefault(key, []).append(item)
        
        logger.info(f"تم العثور على {len(groups)} فئة للتقسيم الطبقي")
        
        # تقسيم كل فئة بشكل مستقل
        train_data, val_data, test_data = [], [], []
        for category, group_items in groups.items():
            t, v, te = self._random_split(group_items)
            train_data.extend(t)
            val_data.extend(v)
            test_data.extend(te)
        
        logger.info(
            f"تم التقسيم الطبقي: train={len(train_data)}, "
            f"val={len(val_data)}, test={len(test_data)}"
        )
        
        return train_data, val_data, test_data

    def _temporal_split(
        self, 
        data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """التقسيم التسلسلي - حسب التاريخ"""
        if not self.date_key:
            raise ValueError("يجب تحديد date_key للتقسيم التسلسلي")
        
        # ترتيب البيانات حسب التاريخ
        sorted_data = sorted(
            data, 
            key=lambda x: x.get(self.date_key, "")
        )
        
        n = len(sorted_data)
        train_size = int(n * self.train_ratio)
        val_size = int(n * self.val_ratio)
        
        train_data = sorted_data[:train_size]
        val_data = sorted_data[train_size:train_size + val_size]
        test_data = sorted_data[train_size + val_size:]
        
        logger.info(
            f"تم التقسيم التسلسلي: train={len(train_data)}, "
            f"val={len(val_data)}, test={len(test_data)}"
        )
        
        return train_data, val_data, test_data

    def save_splits(
        self,
        splits: Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]],
        output_dir: Path,
        file_format: str = "json"
    ) -> None:
        """
        حفظ المجموعات الثلاث في ملفات.
        
        Args:
            splits: المجموعات الثلاث (train, val, test)
            output_dir: مسار المجلد للحفظ
            file_format: صيغة الملف (json أو csv)
        """
        import json
        import csv
        
        output_dir.mkdir(parents=True, exist_ok=True)
        train_data, val_data, test_data = splits
        
        if file_format == "json":
            (output_dir / "train.json").write_text(
                json.dumps(train_data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8"
            )
            (output_dir / "val.json").write_text(
                json.dumps(val_data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8"
            )
            (output_dir / "test.json").write_text(
                json.dumps(test_data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8"
            )
        elif file_format == "csv":
            if train_data:
                fieldnames = train_data[0].keys()
                for name, dataset in [("train", train_data), ("val", val_data), ("test", test_data)]:
                    with open(output_dir / f"{name}.csv", 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(dataset)
        
        logger.info(f"تم حفظ التقسيمات في: {output_dir}")
        logger.info(f"   - تدريب: {len(train_data)} عينة")
        logger.info(f"   - تحقق: {len(val_data)} عينة")
        logger.info(f"   - اختبار: {len(test_data)} عينة")

    def get_split_summary(self, splits: Tuple[List, List, List]) -> Dict[str, Any]:
        """
        الحصول على ملخص التقسيم.
        
        Returns:
            قاموس يحتوي على إحصائيات التقسيم
        """
        train_data, val_data, test_data = splits
        total = len(train_data) + len(val_data) + len(test_data)
        
        return {
            "total_samples": total,
            "train_count": len(train_data),
            "val_count": len(val_data),
            "test_count": len(test_data),
            "train_ratio": f"{len(train_data) / total * 100:.1f}%" if total > 0 else "0%",
            "val_ratio": f"{len(val_data) / total * 100:.1f}%" if total > 0 else "0%",
            "test_ratio": f"{len(test_data) / total * 100:.1f}%" if total > 0 else "0%",
            "random_seed": self.random_seed,
            "strategy": self.strategy.value
        }
