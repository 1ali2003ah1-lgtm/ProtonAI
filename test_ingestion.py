"""
ProtonAI - Test Ingestion Module
اختبارات وحدة استيعاب البيانات
"""

import pytest
import json
import tempfile
from pathlib import Path
from ingestion import DataIngestion


@pytest.fixture
def temp_data_dir():
    """إنشاء مجلد مؤقت للاختبارات"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)


@pytest.fixture
def sample_json_file(temp_data_dir):
    """إنشاء ملف JSON تجريبي"""
    data = [
        {"patient_id": "P001", "age": 45, "gender": "M", "tumor_type": "lung"},
        {"patient_id": "P002", "age": -5, "gender": "F", "tumor_type": "brain"}, # سجل مرفوض (عمر سلبي)
        {"patient_id": "P003", "age": 60, "gender": "F", "tumor_type": "breast"}
    ]
    file_path = temp_data_dir / "patients.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return file_path.name


def test_load_json_success(temp_data_dir, sample_json_file):
    """اختبار تحميل ملف JSON بنجاح"""
    ingestion = DataIngestion(temp_data_dir)
    data = ingestion.load_json(sample_json_file)
    assert len(data) == 3
    assert data[0]["patient_id"] == "P001"


def test_validate_and_clean_separates_valid_invalid(temp_data_dir, sample_json_file):
    """اختبار أن الوحدة تفصل بين السجلات الصحيحة والمرفوضة"""
    ingestion = DataIngestion(temp_data_dir)
    raw_data = ingestion.load_json(sample_json_file)
    
    ingestion.validate_and_clean(raw_data)
    
    # P001 و P003 صحيحان، P002 مرفوض بسبب العمر السلبي
    assert ingestion.ingestion_stats["valid_count"] == 2
    assert ingestion.ingestion_stats["invalid_count"] == 1
    assert len(ingestion.get_valid_data()) == 2


def test_get_report_accuracy(temp_data_dir, sample_json_file):
    """اختبار دقة تقرير الاستيعاب"""
    ingestion = DataIngestion(temp_data_dir)
    raw_data = ingestion.load_json(sample_json_file)
    ingestion.validate_and_clean(raw_data)
    
    report = ingestion.get_report()
    assert report["total_processed"] == 3
    assert report["valid_count"] == 2
    assert report["invalid_count"] == 1
    assert report["validation_pass_rate"] == "66.67%"


def test_load_missing_file_raises_error(temp_data_dir):
    """اختبار أن تحميل ملف غير موجود يثير خطأ"""
    ingestion = DataIngestion(temp_data_dir)
    with pytest.raises(FileNotFoundError):
        ingestion.load_json("non_existent_file.json")
