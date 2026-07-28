"""
ProtonAI - Test Lineage Module
اختبارات وحدة تتبع النسب
"""

import pytest
import json
import tempfile
from pathlib import Path
from lineage import DataLineage, TransformationRecord


@pytest.fixture
def temp_lineage_file():
    """إنشاء ملف مؤقت لسجل التتبع"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        yield Path(f.name)


@pytest.fixture
def lineage_system(temp_lineage_file):
    """إنشاء نظام تتبع جديد"""
    return DataLineage(lineage_file=temp_lineage_file)


class TestDataLineage:
    """اختبارات نظام تتبع النسب"""
    
    def test_initialization(self):
        """اختبار التهيئة"""
        lineage = DataLineage()
        assert len(lineage.transformations) == 0
    
    def test_initialization_with_file(self, temp_lineage_file):
        """اختبار التهيئة مع ملف"""
        lineage = DataLineage(lineage_file=temp_lineage_file)
        assert lineage.lineage_file == temp_lineage_file
    
    def test_record_transformation(self, lineage_system):
        """اختبار تسجيل تحوّل"""
        record = lineage_system.record_transformation(
            operation="data_splitting",
            input_source="raw_data.json",
            output_destination="train.json",
            metadata={"train_ratio": 0.7}
        )
        
        assert isinstance(record, TransformationRecord)
        assert record.operation == "data_splitting"
        assert record.input_source == "raw_data.json"
        assert record.output_destination == "train.json"
        assert len(lineage_system.transformations) == 1
    
    def test_record_transformation_with_data_hash(self, lineage_system):
        """اختبار تسجيل تحوّل مع تجزئة البيانات"""
        input_data = [{"patient_id": "P001", "age": 45}]
        output_data = [{"patient_id": "P001"}]
        
        record = lineage_system.record_transformation(
            operation="data_filtering",
            input_source="all_patients.json",
            output_destination="filtered_patients.json",
            input_data=input_data,
            output_data=output_data
        )
        
        assert record.input_hash is not None
        assert record.output_hash is not None
        assert len(record.input_hash) == 64  # SHA256 hash length
    
    def test_get_lineage(self, lineage_system):
        """اختبار الحصول على سجل التتبع الكامل"""
        lineage_system.record_transformation("op1", "input1", "output1")
        lineage_system.record_transformation("op2", "input2", "output2")
        
        lineage = lineage_system.get_lineage()
        assert len(lineage) == 2
        assert lineage[0]["operation"] == "op1"
        assert lineage[1]["operation"] == "op2"
    
    def test_get_lineage_for_operation(self, lineage_system):
        """اختبار الحصول على سجلات عملية محددة"""
        lineage_system.record_transformation("splitting", "input1", "output1")
        lineage_system.record_transformation("validation", "input2", "output2")
        lineage_system.record_transformation("splitting", "input3", "output3")
        
        splitting_records = lineage_system.get_lineage_for_operation("splitting")
        assert len(splitting_records) == 2
        
        validation_records = lineage_system.get_lineage_for_operation("validation")
        assert len(validation_records) == 1
    
    def test_get_last_transformation(self, lineage_system):
        """اختبار الحصول على آخر تحوّل"""
        lineage_system.record_transformation("op1", "input1", "output1")
        lineage_system.record_transformation("op2", "input2", "output2")
        
        last = lineage_system.get_last_transformation()
        assert last["operation"] == "op2"
    
    def test_get_last_transformation_empty(self):
        """اختبار الحصول على آخر تحوّل من سجل فارغ"""
        lineage = DataLineage()
        assert lineage.get_last_transformation() is None
    
    def test_clear_lineage(self, lineage_system):
        """اختبار مسح سجل التتبع"""
        lineage_system.record_transformation("op1", "input1", "output1")
        assert len(lineage_system.transformations) == 1
        
        lineage_system.clear_lineage()
        assert len(lineage_system.transformations) == 0
    
    def test_save_and_load_lineage(self, temp_lineage_file):
        """اختبار الحفظ والتحميل"""
        # إنشاء سجل وحفظه
        lineage1 = DataLineage(lineage_file=temp_lineage_file)
        lineage1.record_transformation("op1", "input1", "output1")
        lineage1.record_transformation("op2", "input2", "output2")
        
        # تحميل السجل في نظام جديد
        lineage2 = DataLineage(lineage_file=temp_lineage_file)
        assert len(lineage2.transformations) == 2
        assert lineage2.transformations[0].operation == "op1"
    
    def test_get_summary(self, lineage_system):
        """اختبار الملخص الإحصائي"""
        lineage_system.record_transformation("splitting", "input1", "output1")
        lineage_system.record_transformation("validation", "input2", "output2")
        lineage_system.record_transformation("splitting", "input3", "output3")
        
        summary = lineage_system.get_summary()
        assert summary["total_transformations"] == 3
        assert len(summary["operations"]) == 2
        assert "splitting" in summary["operations"]
        assert "validation" in summary["operations"]
    
    def test_get_summary_empty(self):
        """اختبار الملخص لسجل فارغ"""
        lineage = DataLineage()
        summary = lineage.get_summary()
        assert summary["total_transformations"] == 0
    
    def test_verify_data_integrity_valid(self, lineage_system):
        """اختبار التحقق من سلامة البيانات (صحيح)"""
        data = [{"patient_id": "P001", "age": 45}]
        expected_hash = lineage_system._calculate_hash(data)
        
        assert lineage_system.verify_data_integrity(data, expected_hash) is True
    
    def test_verify_data_integrity_invalid(self, lineage_system):
        """اختبار التحقق من سلامة البيانات (خاطئ)"""
        data = [{"patient_id": "P001", "age": 45}]
        wrong_hash = "wrong_hash_value"
        
        assert lineage_system.verify_data_integrity(data, wrong_hash) is False
    
    def test_transformation_record_to_dict(self):
        """اختبار تحويل السجل إلى قاموس"""
        record = TransformationRecord(
            timestamp="2024-01-01T00:00:00",
            operation="test_op",
            input_source="input.json",
            output_destination="output.json"
        )
        
        record_dict = record.to_dict()
        assert isinstance(record_dict, dict)
        assert record_dict["operation"] == "test_op"
        assert record_dict["timestamp"] == "2024-01-01T00:00:00"
    
    def test_auto_save_on_record(self, temp_lineage_file):
        """اختبار الحفظ التلقائي عند التسجيل"""
        lineage = DataLineage(lineage_file=temp_lineage_file)
        lineage.record_transformation("op1", "input1", "output1")
        
        # التحقق من أن الملف تم إنشاؤه
        assert temp_lineage_file.exists()
        
        # قراءة الملف والتحقق من المحتوى
        with open(temp_lineage_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert len(data) == 1
    
    def test_multiple_operations_tracking(self, lineage_system):
        """اختبار تتبع عمليات متعددة"""
        operations = ["ingestion", "validation", "splitting", "normalization"]
        
        for op in operations:
            lineage_system.record_transformation(
                operation=op,
                input_source=f"{op}_input.json",
                output_destination=f"{op}_output.json"
            )
        
        assert len(lineage_system.transformations) == 4
        summary = lineage_system.get_summary()
        assert summary["unique_operations_count"] == 4
