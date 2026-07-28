"""
ProtonAI - Data Splitter Module
مسؤول عن تقسيم البيانات بشكل عشوائي ومكرر (Reproducible)
لضمان عدم تسرب البيانات (Data Leakage) بين التدريب والاختبار.
"""

import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict, Any
import json


class DataSplitter:
    """
    مقسم البيانات الاحترافي لمنصة ProtonAI.
    يدعم التقسيم العشوائي، الطبقي (Stratified)، والتسلسلي (Temporal).
    """

    def __init__(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        stratify_key: str = None
    ):
        """
        تهيئة مقسم البيانات.
        
        Args:
            train_ratio: نسبة بيانات التدريب
            val_ratio: نسبة بيانات التحقق
            test_ratio: نسبة بيانات الاختبار
            random_seed: البذرة العشوائية لضمان التكرار
            stratify_key: مفتاح التقسيم الطبقي (مثل نوع الورم)
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
            "مجموع النسب يجب أن يساوي 1.0"
        
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.stratify_key = stratify_key

    def split(
        self, 
        data: List[Dict[str, Any]]
    ) -> Tuple[List, List, List]:
        """
        تقسيم البيانات إلى ثلاث مجموعات.
        
        Args:
            data: قائمة من القواميس تمثل بيانات المرضى
            
        Returns:
            Tuple تحتوي على (train_data, val_data, test_data)
        """
        if not data:
            raise ValueError("قائمة البيانات فارغة!")

        # تثبيت البذرة العشوائية للتكرار
        rng = np.random.RandomState(self.random_seed)
        
        # تحويل البيانات إلى مصفوفة للتعامل معها
        data_array = np.array(data, dtype=object)
        n_samples = len(data_array)

        # إنشاء مؤشرات عشوائية
        indices = rng.permutation(n_samples)

        # حساب أحجام المجموعات
        train_size = int(n_samples * self.train_ratio)
        val_size = int(n_samples * self.val_ratio)

        # التقسيم
        train_indices = indices[:train_size]
        val_indices = indices[train_size:train_size + val_size]
        test_indices = indices[train_size + val_size:]

        train_data = [data[i] for i in train_indices]
        val_data = [data[i] for i in val_indices]
        test_data = [data[i] for i in test_indices]

        return train_data, val_data, test_data

    def split_with_stratification(
        self,
        data: List[Dict[str, Any]]
    ) -> Tuple[List, List, List]:
        """
        تقسيم طبقي يحافظ على توزيع الفئات في كل مجموعة.
        """
        if not self.stratify_key:
            return self.split(data)

        # تجميع البيانات حسب الفئة
        groups: Dict[Any, List] = {}
        for item in data:
            key = item.get(self.stratify_key, "unknown")
            groups.setdefault(key, []).append(item)

        train_data, val_data, test_data = [], [], []

        # تقسيم كل فئة بشكل مستقل
        for key, group_items in groups.items():
            t, v, te = self.split(group_items)
            train_data.extend(t)
            val_data.extend(v)
            test_data.extend(te)

        return train_data, val_data, test_data

    def save_splits(
        self,
        splits: Tuple[List, List, List],
        output_dir: Path
    ) -> None:
        """
        حفظ المجموعات الثلاث في ملفات JSON.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        train_data, val_data, test_data = splits
        
        (output_dir / "train.json").write_text(
            json.dumps(train_data, indent=2, default=str),
            encoding="utf-8"
        )
        (output_dir / "val.json").write_text(
            json.dumps(val_data, indent=2, default=str),
            encoding="utf-8"
        )
        (output_dir / "test.json").write_text(
            json.dumps(test_data, indent=2, default=str),
            encoding="utf-8"
        )

        print(f"✅ تم حفظ التقسيمات في: {output_dir}")
        print(f"   - تدريب: {len(train_data)} عينة")
        print(f"   - تحقق: {len(val_data)} عينة")
        print(f"   - اختبار: {len(test_data)} عينة")


# ======================== اختبار سريع ========================
if __name__ == "__main__":
    # بيانات تجريبية
    sample_data = [
        {"patient_id": i, "tumor_type": "A" if i % 2 == 0 else "B", "dose": 70.0}
        for i in range(100)
    ]

    splitter = DataSplitter(random_seed=42)
    train, val, test = splitter.split(sample_data)
    
    print(f"📊 نتائج التقسيم:")
    print(f"   Training: {len(train)}")
    print(f"   Validation: {len(val)}")
    print(f"   Test: {len(test)}")
    print(f"   المجموع: {len(train) + len(val) + len(test)}")
