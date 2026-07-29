"""
ProtonAI - Test Normalizers Module
اختبارات وحدة تطبيع البيانات
"""

import pytest
from normalizers import DataNormalizer, NormalizationStrategy, MissingValueStrategy


@pytest.fixture
def sample_patient_data():
    """بيانات مرضى تجريبية"""
    return [
        {"patient_id": "P1", "age": 40, "dose_gy": 60.0, "tumor_volume": 100},
        {"patient_id": "P2", "age": 60, "dose_gy": 70.0, "tumor_volume": 200},
        {"patient_id": "P3", "age": 80, "dose_gy": 80.0, "tumor_volume": 300},
        {"patient_id": "P4", "age": None, "dose_gy": 50.0, "tumor_volume": 150}, # قيمة مفقودة
    ]


class TestDataNormalizer:
    """اختبارات المطبع"""
    
    def test_initialization(self):
        """اختبار التهيئة"""
        normalizer = DataNormalizer(feature_keys=["age", "dose_gy"])
        assert normalizer.feature_keys == ["age", "dose_gy"]
        assert normalizer.is_fitted is False

    def test_fit_calculates_stats(self, sample_patient_data):
        """اختبار حساب الإحصائيات"""
        normalizer = DataNormalizer(feature_keys=["age", "dose_gy"])
        normalizer.fit(sample_patient_data)
        
        stats = normalizer.get_stats()
        assert stats["age"]["min"] == 40.0
        assert stats["age"]["max"] == 80.0
        assert stats["dose_gy"]["mean"] == 65.0
        assert normalizer.is_fitted is True

    def test_fit_empty_data_raises_error(self):
        """اختبار بيانات فارغة"""
        normalizer = DataNormalizer(feature_keys=["age"])
        with pytest.raises(ValueError):
            normalizer.fit([])

    def test_transform_before_fit_raises_error(self, sample_patient_data):
        """اختبار التطبيع قبل الحساب"""
        normalizer = DataNormalizer(feature_keys=["age"])
        with pytest.raises(RuntimeError):
            normalizer.transform(sample_patient_data)

    def test_minmax_normalization(self, sample_patient_data):
        """اختبار تطبيع Min-Max"""
        normalizer = DataNormalizer(
            feature_keys=["age"], 
            strategy=NormalizationStrategy.MINMAX
        )
        result = normalizer.fit_transform(sample_patient_data)
        
        # العمر 40 هو الأدنى -> يجب أن يصبح 0.0
        assert result[0]["age"] == 0.0
        # العمر 80 هو الأعلى -> يجب أن يصبح 1.0
        assert result[2]["age"] == 1.0
        # العمر 60 هو المنتصف -> يجب أن يصبح 0.5
        assert result[1]["age"] == 0.5

    def test_zscore_normalization(self, sample_patient_data):
        """اختبار تطبيع Z-Score"""
        normalizer = DataNormalizer(
            feature_keys=["age"], 
            strategy=NormalizationStrategy.ZSCORE
        )
        result = normalizer.fit_transform(sample_patient_data)
        
        # المتوسط يجب أن يكون قريباً من 0
        # القيم الأقل من المتوسط سالبة، والأعلى موجبة
        assert result[0]["age"] < 0  # 40 أقل من المتوسط
        assert result[2]["age"] > 0  # 80 أعلى من المتوسط

    def test_max_dose_normalization(self, sample_patient_data):
        """اختبار تطبيع الجرعة الأقصى (مهم للبروتون)"""
        normalizer = DataNormalizer(
            feature_keys=["dose_gy"], 
            strategy=NormalizationStrategy.MAX_DOSE
        )
        result = normalizer.fit_transform(sample_patient_data)
        
        # أقصى جرعة 80.0 -> يجب أن تصبح 1.0
        assert result[2]["dose_gy"] == 1.0
        # جرعة 40.0 (لو كانت موجودة) -> 0.5
        # جرعة 60.0 -> 60/80 = 0.75
        assert result[0]["dose_gy"] == pytest.approx(0.75, rel=1e-2)

    def test_missing_value_handling_mean(self, sample_patient_data):
        """اختبار التعامل مع القيم المفقودة (المتوسط)"""
        normalizer = DataNormalizer(
            feature_keys=["age"], 
            missing_strategy=MissingValueStrategy.MEAN
        )
        result = normalizer.fit_transform(sample_patient_data)
        
        # المريض P4 عمره None، سيتم تعويضه بالمتوسط
        # المتوسط الحسابي لـ 40, 60, 80 هو 60
        # بعد MinMax: (60 - 40) / (80 - 40) = 0.5
        assert result[3]["age"] == pytest.approx(0.5, rel=1e-2)

    def test_missing_value_handling_zero(self, sample_patient_data):
        """اختبار التعامل مع القيم المفقودة (صفر)"""
        normalizer = DataNormalizer(
            feature_keys=["age"], 
            missing_strategy=MissingValueStrategy.ZERO
        )
        # نحتاج fit أولاً لحساب الـ min والـ max
        normalizer.fit(sample_patient_data)
        
        # نقوم بتطبيع قيمة صفر يدوياً للتحقق
        # (0 - 40) / (80 - 40) = -1.0
        normalized_val = normalizer._apply_normalization("age", 0.0)
        assert normalized_val == -1.0

    def test_clipping_values(self, sample_patient_data):
        """اختبار قص القيم (Clipping)"""
        normalizer = DataNormalizer(
            feature_keys=["age"], 
            strategy=NormalizationStrategy.MINMAX,
            clip_min=0.2,
            clip_max=0.8
        )
        result = normalizer.fit_transform(sample_patient_data)
        
        # القيمة 0.0 يجب أن تُقص إلى 0.2
        assert result[0]["age"] == 0.2
        # القيمة 1.0 يجب أن تُقص إلى 0.8
        assert result[2]["age"] == 0.8

    def test_fit_transform_consistency(self, sample_patient_data):
        """اختبار تطابق fit() ثم transform() مع fit_transform()"""
        # الطريقة 1
        norm1 = DataNormalizer(feature_keys=["dose_gy"])
        res1 = norm1.fit_transform(sample_patient_data)
        
        # الطريقة 2
        norm2 = DataNormalizer(feature_keys=["dose_gy"])
        norm2.fit(sample_patient_data)
        res2 = norm2.transform(sample_patient_data)
        
        assert res1[0]["dose_gy"] == res2[0]["dose_gy"]
        assert res1[1]["dose_gy"] == res2[1]["dose_gy"]

    def test_multiple_features(self, sample_patient_data):
        """اختبار تطبيع عدة ميزات معاً"""
        normalizer = DataNormalizer(
            feature_keys=["age", "dose_gy", "tumor_volume"],
            strategy=NormalizationStrategy.MINMAX
        )
        result = normalizer.fit_transform(sample_patient_data)
        
        # التحقق من أن جميع المفاتيح تم تطبيعها
        assert "age" in result[0]
        assert "dose_gy" in result[0]
        assert "tumor_volume" in result[0]
        
        # التحقق من أن القيم بين 0 و 1 (لأننا لم نستخدم clipping هنا)
        for row in result:
            if row["patient_id"] != "P4": # P4 فيه قيمة مفقودة
                assert 0.0 <= row["age"] <= 1.0
                assert 0.0 <= row["dose_gy"] <= 1.0
