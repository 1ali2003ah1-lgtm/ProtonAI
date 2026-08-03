"""
ProtonAI - FHIR Models (Integration Prep)
نماذج بيانات بصيغة FHIR (المعيار العالمي لتبادل البيانات الطبية)
Patient / ImagingStudy / ServiceRequest / Observation + make_bundle
to_dict → JSON بصيغة FHIR، from_dict ← قراءة، مع تحقق من الحقول الإلزامية
التجهيز فقط: العقود نظيفة والمحوّلات بالقطعة 6؛ الاتصال الحي على الجهاز لاحقاً
الحقول مبسّطة عمداً للتجهيز (ليست كل تفاصيل FHIR)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ProtonAI.FHIRModels")

_GENDERS = {"male", "female", "other", "unknown"}


def reference(resource_type: str, ref_id: str) -> str:
    """مرجع FHIR بصيغة 'Type/id'"""
    return f"{resource_type}/{ref_id}"


@dataclass
class FHIRPatient:
    """مريض FHIR — المعرّف مخفي الهوية (يربط أمان المرحلة 1)"""
    id: str
    identifier_value: str          # المعرّف المجهّل
    identifier_system: str = "urn:protonai:anonymized"
    gender: Optional[str] = None

    def __post_init__(self):
        if not str(self.id).strip():
            raise ValueError("Patient.id لا يمكن أن يكون فارغاً")
        if not str(self.identifier_value).strip():
            raise ValueError("Patient.identifier_value لا يمكن أن يكون فارغاً")
        if self.gender is not None and self.gender not in _GENDERS:
            raise ValueError(f"gender غير صالح: {self.gender}. المسموح: {_GENDERS}")

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "resourceType": "Patient", "id": self.id,
            "identifier": [{"system": self.identifier_system,
                            "value": self.identifier_value}],
        }
        if self.gender:
            d["gender"] = self.gender
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FHIRPatient":
        ident = (d.get("identifier") or [{}])[0]
        return cls(id=d["id"], identifier_value=ident.get("value", ""),
                   identifier_system=ident.get("system", "urn:protonai:anonymized"),
                   gender=d.get("gender"))


@dataclass
class FHIRImagingStudy:
    """دراسة تصوير FHIR (CT/MRI) مرتبطة بمريض"""
    id: str
    subject_id: str
    modality: str = "CT"
    status: str = "available"
    number_of_series: Optional[int] = None

    def __post_init__(self):
        if not str(self.id).strip():
            raise ValueError("ImagingStudy.id لا يمكن أن يكون فارغاً")
        if not str(self.subject_id).strip():
            raise ValueError("ImagingStudy.subject_id لا يمكن أن يكون فارغاً")

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "resourceType": "ImagingStudy", "id": self.id,
            "status": self.status, "modality": self.modality,
            "subject": {"reference": reference("Patient", self.subject_id)},
        }
        if self.number_of_series is not None:
            d["numberOfSeries"] = self.number_of_series
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FHIRImagingStudy":
        return cls(id=d["id"],
                   subject_id=d.get("subject", {}).get("reference", "").split("/")[-1],
                   modality=d.get("modality", "CT"), status=d.get("status", "available"),
                   number_of_series=d.get("numberOfSeries"))


@dataclass
class FHIRServiceRequest:
    """طلب خدمة FHIR (طلب علاج البروتون)"""
    id: str
    subject_id: str
    code_text: str = "proton_therapy"
    status: str = "active"
    intent: str = "order"

    def __post_init__(self):
        if not str(self.id).strip():
            raise ValueError("ServiceRequest.id لا يمكن أن يكون فارغاً")
        if not str(self.subject_id).strip():
            raise ValueError("ServiceRequest.subject_id لا يمكن أن يكون فارغاً")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resourceType": "ServiceRequest", "id": self.id,
            "status": self.status, "intent": self.intent,
            "code": {"text": self.code_text},
            "subject": {"reference": reference("Patient", self.subject_id)},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FHIRServiceRequest":
        return cls(id=d["id"],
                   subject_id=d.get("subject", {}).get("reference", "").split("/")[-1],
                   code_text=d.get("code", {}).get("text", "proton_therapy"),
                   status=d.get("status", "active"), intent=d.get("intent", "order"))


@dataclass
class FHIRObservation:
    """ملاحظة FHIR (قيمة مقاسة: جرعة/مدى/مؤشر)"""
    id: str
    subject_id: str
    code_text: str
    value: float
    unit: str = "Gy"
    status: str = "final"

    def __post_init__(self):
        if not str(self.id).strip():
            raise ValueError("Observation.id لا يمكن أن يكون فارغاً")
        if not str(self.subject_id).strip():
            raise ValueError("Observation.subject_id لا يمكن أن يكون فارغاً")
        v = float(self.value)
        if v != v or v in (float("inf"), float("-inf")):  # NaN/Inf مرفوضة
            raise ValueError("Observation.value يجب أن يكون رقماً منتهياً")
        self.value = v

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resourceType": "Observation", "id": self.id,
            "status": self.status, "code": {"text": self.code_text},
            "subject": {"reference": reference("Patient", self.subject_id)},
            "valueQuantity": {"value": self.value, "unit": self.unit},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FHIRObservation":
        vq = d.get("valueQuantity", {})
        return cls(id=d["id"],
                   subject_id=d.get("subject", {}).get("reference", "").split("/")[-1],
                   code_text=d.get("code", {}).get("text", ""),
                   value=vq.get("value", 0.0), unit=vq.get("unit", "Gy"),
                   status=d.get("status", "final"))


def make_bundle(resources: List[Any], bundle_type: str = "collection") -> Dict[str, Any]:
    """لفّ موارد FHIR بحزمة (Bundle) جاهزة للإرسال"""
    return {
        "resourceType": "Bundle", "type": bundle_type,
        "entry": [{"resource": r.to_dict()} for r in resources],
  }
