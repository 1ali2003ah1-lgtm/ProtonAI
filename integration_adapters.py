"""
ProtonAI - Integration Adapters (PACS/HIS/RIS/FHIR Prep)
طبقة التكيّف: محوّل FHIR (خطة → Bundle) + عقود واجهات + Hub ناشر
IntegrationAdapter = العقد (ABC)؛ الموصلات الحقيقية (DICOM-web/HL7) تركّب على الجهاز
InMemoryIntegrationAdapter = تنفيذ اختبار/ديمو. الـ Hub ما يعرف البروتوكولات، بس العقد
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from fhir_models import (
    FHIRPatient, FHIRImagingStudy, FHIRServiceRequest, FHIRObservation, make_bundle,
)

logger = logging.getLogger("ProtonAI.IntegrationAdapters")


class FHIRMapper:
    """محوّل: كائنات المنصة الداخلية → موارد FHIR"""

    def patient_to_fhir(self, patient_id: str, gender: Optional[str] = None) -> FHIRPatient:
        """مريض FHIR مجهّل (المعرّف الداخلي = المعرّف المجهّل)"""
        return FHIRPatient(patient_id, patient_id, gender=gender)

    def plan_to_bundle(self, plan: Any, bundle_type: str = "collection") -> Dict[str, Any]:
        """خطة علاج كاملة → Bundle FHIR (Patient + Imaging + Request + Observations)"""
        pid = plan.patient_id
        resources: List[Any] = [self.patient_to_fhir(pid)]

        img = getattr(plan, "imaging", None) or {}
        resources.append(FHIRImagingStudy(
            f"st_{plan.plan_id}", pid,
            modality=str(img.get("modality", "CT")),
            number_of_series=img.get("slices")))

        resources.append(FHIRServiceRequest(f"sr_{plan.plan_id}", pid))

        # Observation لكل مقياس فيزيائي رقمي (نتجاوز bool عمداً)
        phys = getattr(plan, "physics", None) or {}
        for key, val in phys.items():
            if isinstance(val, bool):
                continue
            if isinstance(val, (int, float)):
                resources.append(FHIRObservation(
                    f"ob_{plan.plan_id}_{key}", pid, str(key), float(val), unit="1"))

        return make_bundle(resources, bundle_type)


class IntegrationAdapter(ABC):
    """العقد اللي أي موصل (PACS/HIS/RIS) لازم ينفّذه"""
    system_name: str = "abstract"

    @abstractmethod
    def send(self, bundle: Dict[str, Any]) -> str:
        """إرسال Bundle، يرجع إيصال (ack id)"""

    @abstractmethod
    def fetch(self, ref: str) -> Optional[Dict[str, Any]]:
        """جلب مورد بالمرجع، أو None"""

    def is_connected(self) -> bool:
        """افتراضي متصل؛ الموصلات الحقيقية تتحقق من الشبكة"""
        return True


class InMemoryIntegrationAdapter(IntegrationAdapter):
    """تنفيذ داخلي للاختبار/الديمو (يخزن بالذاكرة)"""

    def __init__(self, system_name: str = "memory"):
        self.system_name = system_name
        self.sent: List[Dict[str, Any]] = []
        self.store: Dict[str, Dict[str, Any]] = {}

    def send(self, bundle: Dict[str, Any]) -> str:
        self.sent.append(bundle)
        ack = f"ack_{self.system_name}_{len(self.sent)}"
        logger.info(f"{self.system_name}: أُرسل bundle ({len(bundle.get('entry', []))} موارد)")
        return ack

    def fetch(self, ref: str) -> Optional[Dict[str, Any]]:
        return self.store.get(ref)

    def put(self, ref: str, resource: Dict[str, Any]) -> None:
        """تحميل مورد للاختبار"""
        self.store[ref] = resource


class IntegrationHub:
    """
    ناشر التكامل: يسجّل الموصولات وينشر الخطط لها كلها.
    ما يعرف البروتوكولات — يتعامل مع العقد (IntegrationAdapter) فقط.
    """

    def __init__(self, mapper: Optional[FHIRMapper] = None):
        self.mapper = mapper if mapper is not None else FHIRMapper()
        self.adapters: Dict[str, IntegrationAdapter] = {}

    def register(self, adapter: IntegrationAdapter) -> None:
        """تسجيل موصل باسم نظامه"""
        self.adapters[adapter.system_name] = adapter

    def publish(self, plan: Any) -> Dict[str, Any]:
        """تحويل الخطة لـ Bundle وإرسالها لكل الموصولات، يرجع الإيصالات"""
        bundle = self.mapper.plan_to_bundle(plan)
        acks = {name: ad.send(bundle) for name, ad in self.adapters.items()}
        logger.info(f"hub: نُشرت الخطة إلى {list(acks.keys())}")
        return {"bundle": bundle, "acks": acks}
