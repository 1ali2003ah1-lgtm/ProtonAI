"""
ProtonAI - Data Lineage Module
وحدة تتبع أصل البيانات والتحولات
تضمن إمكانية إعادة إنتاج النتائج (Reproducibility)
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


logger = logging.getLogger("ProtonAI.Lineage")


@dataclass
class TransformationRecord:
    """سجل تحوّل البيانات"""
    
    timestamp: str
    operation: str
    input_source: str
    output_destination: str
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    metadata: Dict[str, Any] = None
    performer: str = "ProtonAI System"
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل السجل إلى قاموس"""
        return asdict(self)


class DataLineage:
    """
    نظام تتبع أصل البيانات الاحترافي.
    يسجل كل تحوّل يحدث للبيانات مع الطابع الزمني والتجزئة (Hash).
    """

    def __init__(self, lineage_file: Optional[str | Path] = None):
        """
        تهيئة نظام التتبع.
        
        Args:
            lineage_file: مسار ملف JSON لحفظ سجل التتبع (اختياري)
        """
        self.lineage_file = Path(lineage_file) if lineage_file else None
        self.transformations: List[TransformationRecord] = []
        
        # تحميل السجل السابق إذا كان موجوداً
        if self.lineage_file and self.lineage_file.exists():
            self._load_lineage()
            logger.info(f"تم تحميل {len(self.transformations)} سجل تتبع سابق")
        
        logger.info("تم تهيئة نظام تتبع النسب")

    def record_transformation(
        self,
        operation: str,
        input_source: str,
        output_destination: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        performer: str = "ProtonAI System"
    ) -> TransformationRecord:
        """
        تسجيل عملية تحوّل جديدة.
        
        Args:
            operation: اسم العملية (مثل "data_splitting", "validation", "normalization")
            input_source: مصدر البيانات المدخلة
            output_destination: وجهة البيانات المخرجة
            input_data: البيانات المدخلة (اختياري، لحساب التجزئة)
            output_data: البيانات المخرجة (اختياري، لحساب التجزئة)
            metadata: بيانات إضافية عن العملية
            performer: منفذ العملية
            
        Returns:
            TransformationRecord: السجل المنشأ
        """
        # حساب تجزئة البيانات (Hash) للتأكد من عدم التلاعب
        input_hash = self._calculate_hash(input_data) if input_data is not None else None
        output_hash = self._calculate_hash(output_data) if output_data is not None else None
        
        record = TransformationRecord(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            input_source=input_source,
            output_destination=output_destination,
            input_hash=input_hash,
            output_hash=output_hash,
            metadata=metadata or {},
            performer=performer
        )
        
        self.transformations.append(record)
        
        # حفظ تلقائي إذا تم تحديد ملف
        if self.lineage_file:
            self._save_lineage()
        
        logger.info(f"تم تسجيل تحوّل: {operation} من {input_source} إلى {output_destination}")
        
        return record

    def _calculate_hash(self, data: Any) -> str:
        """
        حساب تجزئة SHA256 للبيانات.
        
        Args:
            data: البيانات المراد تجزئتها
            
        Returns:
            str: التجزئة بصيغة hex
        """
        try:
            # تحويل البيانات إلى نص JSON
            data_str = json.dumps(data, sort_keys=True, default=str)
            # حساب التجزئة
            return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.warning(f"فشل حساب التجزئة: {e}")
            return "hash_calculation_failed"

    def get_lineage(self) -> List[Dict[str, Any]]:
        """
        الحصول على سجل التتبع الكامل.
        
        Returns:
            List[Dict[str, Any]]: قائمة بسجلات التحوّلات
        """
        return [record.to_dict() for record in self.transformations]

    def get_lineage_for_operation(self, operation: str) -> List[Dict[str, Any]]:
        """
        الحصول على سجلات تحوّل محددة.
        
        Args:
            operation: اسم العملية المطلوبة
            
        Returns:
            List[Dict[str, Any]]: سجلات العملية المحددة
        """
        return [
            record.to_dict() 
            for record in self.transformations 
            if record.operation == operation
        ]

    def get_last_transformation(self) -> Optional[Dict[str, Any]]:
        """
        الحصول على آخر تحوّل مسجل.
        
        Returns:
            Optional[Dict[str, Any]]: آخر سجل أو None
        """
        if not self.transformations:
            return None
        return self.transformations[-1].to_dict()

    def clear_lineage(self) -> None:
        """مسح سجل التتبع"""
        self.transformations.clear()
        if self.lineage_file and self.lineage_file.exists():
            self.lineage_file.unlink()
        logger.info("تم مسح سجل التتبع")

    def _save_lineage(self) -> None:
        """حفظ سجل التتبع في ملف JSON"""
        if not self.lineage_file:
            return
        
        self.lineage_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = self.get_lineage()
        with open(self.lineage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"تم حفظ {len(data)} سجل تتبع في {self.lineage_file}")

    def _load_lineage(self) -> None:
        """تحميل سجل التتبع من ملف JSON"""
        if not self.lineage_file or not self.lineage_file.exists():
            return
        
        try:
            with open(self.lineage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.transformations = [
                TransformationRecord(**record) 
                for record in data
            ]
            logger.info(f"تم تحميل {len(self.transformations)} سجل تتبع")
        except Exception as e:
            logger.error(f"فشل تحميل سجل التتبع: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """
        الحصول على ملخص إحصائي لسجل التتبع.
        
        Returns:
            Dict[str, Any]: إحصائيات السجل
        """
        if not self.transformations:
            return {
                "total_transformations": 0,
                "operations": [],
                "first_transformation": None,
                "last_transformation": None
            }
        
        operations = list(set(record.operation for record in self.transformations))
        
        return {
            "total_transformations": len(self.transformations),
            "operations": operations,
            "first_transformation": self.transformations[0].timestamp,
            "last_transformation": self.transformations[-1].timestamp,
            "unique_operations_count": len(operations)
        }

    def verify_data_integrity(
        self,
        data: Any,
        expected_hash: str
    ) -> bool:
        """
        التحقق من سلامة البيانات بمقارنة التجزئة.
        
        Args:
            data: البيانات المراد التحقق منها
            expected_hash: التجزئة المتوقعة
            
        Returns:
            bool: True إذا كانت التجزئة متطابقة
        """
        actual_hash = self._calculate_hash(data)
        is_valid = actual_hash == expected_hash
        
        if not is_valid:
            logger.warning(
                f"فشل التحقق من سلامة البيانات! "
                f"المتوقع: {expected_hash}, الفعلي: {actual_hash}"
            )
        else:
            logger.info("تم التحقق من سلامة البيانات بنجاح")
        
        return is_valid
