"""
ProtonAI - Test Split Module
اختبارات وحدة تقسيم البيانات
"""

import pytest
from split import DataSplitter, SplitStrategy


@pytest.fixture
def sample_data():
    """بيانات تجريبية"""
    return [
        {"patient_id": f"P{i:03d}", "age": 30 + i, "tumor_type": "lung" if i % 2 == 0 else "brain"}
        for i in range(100)
    ]


class TestDataSplitter:
    """اختبارات مقسم البيانات"""
    
    def test_initialization_valid_ratios(self):
        """اختبار تهيئة بنسب صحيحة"""
        splitter = DataSplitter(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
        assert splitter.train_ratio == 0.7
        assert splitter.val_ratio == 0.15
        assert splitter.test_ratio == 0.15
    
    def test_initialization_invalid_ratios(self):
        """اختبار تهيئة بنسب خاطئة"""
        with pytest.raises(ValueError):
            DataSplitter(train_ratio=0.5, val_ratio=0.5, test_ratio=0.5)
    
    def test_random_split_sizes(self, sample_data):
        """اختبار أحجام التقسيم العشوائي"""
        splitter = DataSplitter(random_seed=42)
        train, val, test = splitter.split(sample_data)
        
        assert len(train) == 70
        assert len(val) == 15
        assert len(test) == 15
        assert len(train) + len(val) + len(test) == 100
    
    def test_random_split_reproducibility(self, sample_data):
        """اختبار التكرارية - نفس البذرة تعطي نفس النتيجة"""
        splitter1 = DataSplitter(random_seed=42)
        splitter2 = DataSplitter(random_seed=42)
        
        train1, val1, test1 = splitter1.split(sample_data)
        train2, val2, test2 = splitter2.split(sample_data)
        
        assert train1 == train2
        assert val1 == val2
        assert test1 == test2
    
    def test_random_split_different_seeds(self, sample_data):
        """اختبار أن بذور مختلفة تعطي نتائج مختلفة"""
        splitter1 = DataSplitter(random_seed=42)
        splitter2 = DataSplitter(random_seed=99)
        
        train1, _, _ = splitter1.split(sample_data)
        train2, _, _ = splitter2.split(sample_data)
        
        # من المستحيل أن تكون النتائج متطابقة (احتمال ضئيل جداً)
        assert train1 != train2
    
    def test_stratified_split(self, sample_data):
        """اختبار التقسيم الطبقي"""
        splitter = DataSplitter(
            strategy=SplitStrategy.STRATIFIED,
            stratify_key="tumor_type",
            random_seed=42
        )
        train, val, test = splitter.split(sample_data)
        
        assert len(train) + len(val) + len(test) == 100
        
        # التحقق من أن كل مجموعة تحتوي على الفئتين
        train_types = set(item["tumor_type"] for item in train)
        assert "lung" in train_types
        assert "brain" in train_types
    
    def test_stratified_split_missing_key(self, sample_data):
        """اختبار التقسيم الطبقي بدون مفتاح"""
        splitter = DataSplitter(strategy=SplitStrategy.STRATIFIED)
        with pytest.raises(ValueError):
            splitter.split(sample_data)
    
    def test_temporal_split(self):
        """اختبار التقسيم التسلسلي"""
        data = [
            {"patient_id": f"P{i}", "date": f"2024-{i:02d}-01"}
            for i in range(1, 101)
        ]
        
        splitter = DataSplitter(
            strategy=SplitStrategy.TEMPORAL,
            date_key="date"
        )
        train, val, test = splitter.split(data)
        
        # التحقق من أن البيانات مرتبة زمنياً
        assert train[0]["date"] < train[-1]["date"]
        assert train[-1]["date"] < val[0]["date"]
        assert val[-1]["date"] < test[0]["date"]
    
    def test_empty_data_raises_error(self):
        """اختبار بيانات فارغة"""
        splitter = DataSplitter()
        with pytest.raises(ValueError):
            splitter.split([])
    
    def test_get_split_summary(self, sample_data):
        """اختبار ملخص التقسيم"""
        splitter = DataSplitter(random_seed=42)
        splits = splitter.split(sample_data)
        summary = splitter.get_split_summary(splits)
        
        assert summary["total_samples"] == 100
        assert summary["train_count"] == 70
        assert summary["val_count"] == 15
        assert summary["test_count"] == 15
        assert summary["random_seed"] == 42
        assert summary["strategy"] == "random"
    
    def test_save_splits_json(self, sample_data, tmp_path):
        """اختبار حفظ التقسيمات بصيغة JSON"""
        from pathlib import Path
        
        splitter = DataSplitter(random_seed=42)
        splits = splitter.split(sample_data)
        splitter.save_splits(splits, tmp_path, file_format="json")
        
        assert (tmp_path / "train.json").exists()
        assert (tmp_path / "val.json").exists()
        assert (tmp_path / "test.json").exists()
    
    def test_different_ratios(self, sample_data):
        """اختبار نسب تقسيم مختلفة"""
        splitter = DataSplitter(
            train_ratio=0.8,
            val_ratio=0.1,
            test_ratio=0.1,
            random_seed=42
        )
        train, val, test = splitter.split(sample_data)
        
        assert len(train) == 80
        assert len(val) == 10
        assert len(test) == 10
