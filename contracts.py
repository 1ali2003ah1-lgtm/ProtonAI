"""
ProtonAI - Data Contracts
عقود البيانات الاحترافية للعلاج بالبروتون (Pydantic V2 Compliant)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class TumorType(str, Enum):
    """أنواع الأورام المدعومة"""
    LUNG = "lung"
    BRAIN = "brain"
    PROSTATE = "prostate"
    BREAST = "breast"
    HEAD_NECK = "head_neck"
    OTHER = "other"


class PatientData(BaseModel):
    """نموذج بيانات المريض الاحترافي"""
    
    # تحديث إعدادات النموذج لمعايير Pydantic V2
    model_config = ConfigDict(use_enum_values=True)
    
    patient_id: str = Field(..., min_length=1, description="معرف المريض الفريد")
    age: int = Field(..., ge=0, le=120, description="عمر المريض بالسنوات")
    gender: str = Field(..., description="الجنس (M/F)")
    tumor_type: TumorType = Field(..., description="نوع الورم")
    diagnosis_date: Optional[datetime] = Field(None, description="تاريخ التشخيص")
    
    @field_validator('patient_id')
    @classmethod
    def validate_patient_id(cls, v: str) -> str:
        """التحقق من معرف المريض"""
        v = v.strip()
        if not v:
            raise ValueError('Patient ID cannot be empty')
        return v
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """التحقق من الجنس"""
        v = v.upper()
        if v not in ['M', 'F', 'MALE', 'FEMALE']:
            raise ValueError('Gender must be M or F')
        return v[0]  # Return 'M' or 'F'


class TreatmentPlan(BaseModel):
    """نموذج خطة العلاج"""
    
    plan_id: str = Field(..., description="معرف خطة العلاج")
    patient_id: str = Field(..., description="معرف المريض")
    total_dose_gy: float = Field(..., gt=0, le=100, description="الجرعة الكلية (Gy)")
    fractions: int = Field(..., gt=0, le=50, description="عدد الجلسات")
    
    @field_validator('total_dose_gy')
    @classmethod
    def validate_dose(cls, v: float) -> float:
        """التحقق من الجرعة"""
        if v < 10 or v > 100:
            raise ValueError('Total dose must be between 10 and 100 Gy')
        return v
    
    @property
    def dose_per_fraction(self) -> float:
        """الجرعة لكل جلسة"""
        return self.total_dose_gy / self.fractions
