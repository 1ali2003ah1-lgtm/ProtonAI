"""
ProtonAI - Data Contracts
عقود البيانات الاحترافية للعلاج بالبروتون
"""

from pydantic import BaseModel, Field, validator
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
    
    patient_id: str = Field(..., min_length=1, description="معرف المريض الفريد")
    age: int = Field(..., ge=0, le=120, description="عمر المريض بالسنوات")
    gender: str = Field(..., description="الجنس (M/F)")
    tumor_type: TumorType = Field(..., description="نوع الورم")
    diagnosis_date: Optional[datetime] = Field(None, description="تاريخ التشخيص")
    
    class Config:
        use_enum_values = True
    
    @validator('patient_id')
    def validate_patient_id(cls, v):
        """التحقق من معرف المريض"""
        v = v.strip()
        if not v:
            raise ValueError('Patient ID cannot be empty')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        """التحقق من الجنس"""
        v = v.upper()
        if v not in ['M', 'F', 'MALE', 'FEMALE']:
            raise ValueError('Gender must be M or F')
        return v[0]


class TreatmentPlan(BaseModel):
    """نموذج خطة العلاج"""
    
    plan_id: str = Field(..., description="معرف خطة العلاج")
    patient_id: str = Field(..., description="معرف المريض")
    total_dose_gy: float = Field(..., gt=0, le=100, description="الجرعة الكلية (Gy)")
    fractions: int = Field(..., gt=0, le=50, description="عدد الجلسات")
    
    @validator('total_dose_gy')
    def validate_dose(cls, v):
        """التحقق من الجرعة"""
        if v < 10 or v > 100:
            raise ValueError('Total dose must be between 10 and 100 Gy')
        return v
    
    @property
    def dose_per_fraction(self) -> float:
        """الجرعة لكل جلسة"""
        return self.total_dose_gy / self.fractions
