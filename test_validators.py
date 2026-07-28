"""
ProtonAI - Test Suite
مجموعة الاختبارات الاحترافية
"""

import pytest
from validators import CrossFieldValidator, validate_patient_record, validate_dose_distribution


class TestCrossFieldValidator:
    """اختبارات التحقق المتقاطع"""
    
    def test_valid_dose_fractions_standard(self):
        """اختبار جرعة قياسية صحيحة"""
        result = CrossFieldValidator.validate_dose_fractions(70.0, 35)
        assert result is True
    
    def test_valid_dose_fractions_hypofractionated(self):
        """اختبار جرعة عالية (Hypofractionated)"""
        result = CrossFieldValidator.validate_dose_fractions(60.0, 20)
        assert result is True
    
    def test_invalid_dose_too_high_per_fraction(self):
        """اختبار جرعة عالية جداً لكل جلسة"""
        result = CrossFieldValidator.validate_dose_fractions(100.0, 10)
        assert result is False
    
    def test_invalid_dose_too_low_per_fraction(self):
        """اختبار جرعة منخفضة جداً لكل جلسة"""
        result = CrossFieldValidator.validate_dose_fractions(10.0, 35)
        assert result is False
    
    def test_invalid_zero_fractions(self):
        """اختبار عدد جلسات صفر"""
        result = CrossFieldValidator.validate_dose_fractions(70.0, 0)
        assert result is False
    
    def test_valid_age_tumor_lung_adult(self):
        """اختبار سرطان الرئة عند بالغ"""
        result = CrossFieldValidator.validate_age_tumor(65, 'lung')
        assert result is True
    
    def test_invalid_age_tumor_prostate_young(self):
        """اختبار سرطان البروستاتا عند شاب (غير منطقي)"""
        result = CrossFieldValidator.validate_age_tumor(25, 'prostate')
        assert result is False
    
    def test_valid_treatment_plan(self):
        """اختبار خطة علاج صحيحة"""
        plan = {
            'plan_id': 'PLAN001',
            'patient_id': 'P001',
            'total_dose_gy': 70.0,
            'fractions': 35
        }
        result = CrossFieldValidator.validate_treatment_plan(plan)
        assert result is True


class TestValidatePatientRecord:
    """اختبارات التحقق من سجل المريض"""
    
    def test_valid_patient_record(self):
        """اختبار سجل مريض صحيح"""
        record = {
            'patient_id': 'P001',
            'age': 45,
            'gender': 'M',
            'tumor_type': 'lung'
        }
        result = validate_patient_record(record)
        assert result is True
    
    def test_invalid_age_negative(self):
        """اختبار عمر سلبي"""
        record = {
            'patient_id': 'P002',
            'age': -5,
            'gender': 'F',
            'tumor_type': 'brain'
        }
        result = validate_patient_record(record)
        assert result is False
    
    def test_invalid_age_too_high(self):
        """اختبار عمر مرتفع جداً"""
        record = {
            'patient_id': 'P003',
            'age': 150,
            'gender': 'M',
            'tumor_type': 'lung'
        }
        result = validate_patient_record(record)
        assert result is False
    
    def test_invalid_empty_patient_id(self):
        """اختبار معرف مريض فارغ"""
        record = {
            'patient_id': '',
            'age': 45,
            'gender': 'M',
            'tumor_type': 'lung'
        }
        result = validate_patient_record(record)
        assert result is False
    
    def test_valid_patient_with_all_fields(self):
        """اختبار مريض بكل الحقول"""
        from datetime import datetime
        record = {
            'patient_id': 'P004',
            'age': 60,
            'gender': 'F',
            'tumor_type': 'breast',
            'diagnosis_date': datetime.now()
        }
        result = validate_patient_record(record)
        assert result is True


class TestValidateDoseDistribution:
    """اختبارات توزيع الجرعة"""
    
    def test_valid_dose_distribution(self):
        """اختبار توزيع جرعة مثالي"""
        result = validate_dose_distribution(
            target_coverage=98.5,
            max_dose=73.5,
            mean_dose=70.0
        )
        assert result is True
    
    def test_invalid_low_coverage(self):
        """اختبار تغطية منخفضة"""
        result = validate_dose_distribution(
            target_coverage=90.0,
            max_dose=73.5,
            mean_dose=70.0
        )
        assert result is False
    
    def test_invalid_max_dose_too_high(self):
        """اختبار أقصى جرعة مرتفعة جداً"""
        result = validate_dose_distribution(
            target_coverage=98.0,
            max_dose=80.0,
            mean_dose=70.0
        )
        assert result is False
    
    def test_boundary_coverage_95(self):
        """اختبار تغطية 95% بالضبط (الحد الأدنى)"""
        result = validate_dose_distribution(
            target_coverage=95.0,
            max_dose=73.5,
            mean_dose=70.0
        )
        assert result is True
