"""
ProtonAI - Validators
التحقق الاحترافي من البيانات
"""

from typing import Dict, Any
from contracts import PatientData, TreatmentPlan


class CrossFieldValidator:
    """التحقق المتقاطع بين الحقول - احترافي"""
    
    @staticmethod
    def validate_dose_fractions(dose_gy: float, fractions: int) -> bool:
        """
        التحقق من أن الجرعة لكل جلسة ضمن المدى الآمن
        المدى الآمن: 1.8 - 3.0 Gy لكل جلسة
        """
        if fractions <= 0:
            return False
        
        dose_per_fraction = dose_gy / fractions
        
        # المدى المقبول: 1.0 - 5.0 Gy
        return 1.0 <= dose_per_fraction <= 5.0
    
    @staticmethod
    def validate_age_tumor(age: int, tumor_type: str) -> bool:
        """التحقق من تناسب العمر مع نوع الورم"""
        # سرطان البروستاتا نادر جداً تحت 40 سنة
        if tumor_type.lower() == 'prostate' and age < 40:
            return False
        
        return True
    
    @staticmethod
    def validate_treatment_plan(plan_data: Dict[str, Any]) -> bool:
        """التحقق الشامل من خطة العلاج"""
        try:
            plan = TreatmentPlan(**plan_data)
            
            if not CrossFieldValidator.validate_dose_fractions(
                plan.total_dose_gy, 
                plan.fractions
            ):
                return False
            
            return True
        except Exception:
            return False


def validate_patient_record(record: Dict[str, Any]) -> bool:
    """
    التحقق الشامل من سجل المريض
    
    Args:
        record: قاموس يحتوي على بيانات المريض
        
    Returns:
        bool: True إذا كانت البيانات صحيحة
    """
    try:
        patient = PatientData(**record)
        
        if not CrossFieldValidator.validate_age_tumor(
            patient.age, 
            patient.tumor_type
        ):
            return False
        
        return True
    except Exception:
        return False


def validate_dose_distribution(
    target_coverage: float,
    max_dose: float,
    mean_dose: float
) -> bool:
    """
    التحقق من توزيع الجرعة
    
    Args:
        target_coverage: نسبة تغطية الورم (%)
        max_dose: أقصى جرعة (Gy)
        mean_dose: متوسط الجرعة (Gy)
        
    Returns:
        bool: True إذا كان التوزيع مقبول
    """
    if target_coverage < 95:
        return False
    
    if max_dose > mean_dose * 1.1:
        return False
    
    return True
