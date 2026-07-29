"""
ProtonAI - Test Reporters Module
اختبارات وحدة توليد التقارير
"""

import pytest
import json
import tempfile
from pathlib import Path
from reporters import ReportGenerator


@pytest.fixture
def temp_report_dir():
    """إنشاء مجلد مؤقت للتقارير"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)


@pytest.fixture
def report_generator(temp_report_dir):
    """إنشاء مولد تقارير جديد"""
    return ReportGenerator(report_dir=temp_report_dir)


@pytest.fixture
def sample_ingestion_stats():
    """إحصائيات استيعاب تجريبية"""
    return {
        "total_processed": 100,
        "valid_count": 95,
        "invalid_count": 5,
        "validation_pass_rate": "95.00%"
    }


@pytest.fixture
def sample_split_summary():
    """ملخص تقسيم تجريبي"""
    return {
        "total_samples": 100,
        "train_count": 70,
        "val_count": 15,
        "test_count": 15,
        "train_ratio": "70.0%",
        "val_ratio": "15.0%",
        "test_ratio": "15.0%",
        "random_seed": 42,
        "strategy": "random"
    }


@pytest.fixture
def sample_lineage_summary():
    """ملخص تتبع تجريبي"""
    return {
        "total_transformations": 5,
        "operations": ["ingestion", "validation", "splitting"],
        "first_transformation": "2024-01-01T00:00:00",
        "last_transformation": "2024-01-01T01:00:00",
        "unique_operations_count": 3
    }


class TestReportGenerator:
    """اختبارات مولد التقارير"""
    
    def test_initialization(self, temp_report_dir):
        """اختبار التهيئة"""
        generator = ReportGenerator(report_dir=temp_report_dir)
        assert generator.report_dir == temp_report_dir
        assert len(generator.reports) == 0
    
    def test_initialization_without_dir(self):
        """اختبار التهيئة بدون مجلد"""
        generator = ReportGenerator()
        assert generator.report_dir is None
    
    def test_generate_ingestion_report(self, report_generator, sample_ingestion_stats):
        """اختبار توليد تقرير الاستيعاب"""
        report = report_generator.generate_ingestion_report(sample_ingestion_stats)
        
        assert report["report_type"] == "ingestion"
        assert report["title"] == "تقرير استيعاب البيانات"
        assert len(report["sections"]) == 1
        assert report["sections"][0]["data"]["total_processed"] == 100
        assert len(report_generator.reports) == 1
    
    def test_generate_split_report(self, report_generator, sample_split_summary):
        """اختبار توليد تقرير التقسيم"""
        report = report_generator.generate_split_report(sample_split_summary)
        
        assert report["report_type"] == "split"
        assert report["sections"][0]["data"]["train_count"] == 70
        assert len(report_generator.reports) == 1
    
    def test_generate_lineage_report(self, report_generator, sample_lineage_summary):
        """اختبار توليد تقرير التتبع"""
        report = report_generator.generate_lineage_report(sample_lineage_summary)
        
        assert report["report_type"] == "lineage"
        assert report["sections"][0]["data"]["total_transformations"] == 5
        assert len(report_generator.reports) == 1
    
    def test_generate_comprehensive_report(
        self, 
        report_generator, 
        sample_ingestion_stats, 
        sample_split_summary, 
        sample_lineage_summary
    ):
        """اختبار توليد التقرير الشامل"""
        report = report_generator.generate_comprehensive_report(
            ingestion_stats=sample_ingestion_stats,
            split_summary=sample_split_summary,
            lineage_summary=sample_lineage_summary
        )
        
        assert report["report_type"] == "comprehensive"
        assert len(report["sections"]) == 3
        assert report["sections"][0]["title"] == "استيعاب البيانات"
        assert report["sections"][1]["title"] == "تقسيم البيانات"
        assert report["sections"][2]["title"] == "تتبع النسب"
    
    def test_generate_comprehensive_report_partial(
        self, 
        report_generator, 
        sample_ingestion_stats
    ):
        """اختبار التقرير الشامل ببيانات جزئية"""
        report = report_generator.generate_comprehensive_report(
            ingestion_stats=sample_ingestion_stats
        )
        
        assert len(report["sections"]) == 1
    
    def test_save_report_json(self, report_generator, sample_ingestion_stats):
        """اختبار حفظ التقرير بصيغة JSON"""
        report = report_generator.generate_ingestion_report(sample_ingestion_stats)
        file_path = report_generator.save_report(report, "test_report.json")
        
        assert file_path.exists()
        assert file_path.suffix == ".json"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_report = json.load(f)
        
        assert saved_report["report_type"] == "ingestion"
    
    def test_save_report_auto_filename(self, report_generator, sample_ingestion_stats):
        """اختبار الحفظ باسم ملف تلقائي"""
        report = report_generator.generate_ingestion_report(sample_ingestion_stats)
        file_path = report_generator.save_report(report)
        
        assert file_path.exists()
        assert "ingestion" in file_path.name
    
    def test_save_report_without_dir(self, sample_ingestion_stats):
        """اختبار الحفظ بدون تحديد مجلد"""
        generator = ReportGenerator()
        report = generator.generate_ingestion_report(sample_ingestion_stats)
        
        with pytest.raises(ValueError):
            generator.save_report(report)
    
    def test_export_to_markdown(self, report_generator, sample_ingestion_stats):
        """اختبار تصدير التقرير بصيغة Markdown"""
        report = report_generator.generate_ingestion_report(sample_ingestion_stats)
        md_content = report_generator.export_to_markdown(report)
        
        assert isinstance(md_content, str)
        assert "# تقرير استيعاب البيانات" in md_content
        assert "**total_processed:** 100" in md_content
        assert "**valid_count:** 95" in md_content
    
    def test_save_markdown_report(self, report_generator, sample_ingestion_stats):
        """اختبار حفظ تقرير Markdown"""
        report = report_generator.generate_ingestion_report(sample_ingestion_stats)
        file_path = report_generator.save_markdown_report(report, "test_report.md")
        
        assert file_path.exists()
        assert file_path.suffix == ".md"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "# تقرير استيعاب البيانات" in content
    
    def test_get_all_reports(self, report_generator, sample_ingestion_stats):
        """اختبار الحصول على جميع التقارير"""
        report_generator.generate_ingestion_report(sample_ingestion_stats)
        report_generator.generate_ingestion_report(sample_ingestion_stats)
        
        reports = report_generator.get_all_reports()
        assert len(reports) == 2
    
    def test_get_last_report(self, report_generator, sample_ingestion_stats):
        """اختبار الحصول على آخر تقرير"""
        report_generator.generate_ingestion_report(sample_ingestion_stats)
        report_generator.generate_split_report({"total_samples": 50})
        
        last_report = report_generator.get_last_report()
        assert last_report["report_type"] == "split"
    
    def test_get_last_report_empty(self, report_generator):
        """اختبار الحصول على آخر تقرير من قائمة فارغة"""
        assert report_generator.get_last_report() is None
    
    def test_clear_reports(self, report_generator, sample_ingestion_stats):
        """اختبار مسح جميع التقارير"""
        report_generator.generate_ingestion_report(sample_ingestion_stats)
        report_generator.generate_ingestion_report(sample_ingestion_stats)
        
        assert len(report_generator.reports) == 2
        
        report_generator.clear_reports()
        assert len(report_generator.reports) == 0
    
    def test_multiple_report_types(self, report_generator):
        """اختبار توليد أنواع متعددة من التقارير"""
        report_generator.generate_ingestion_report({"total": 10})
        report_generator.generate_split_report({"total": 10})
        report_generator.generate_lineage_report({"total": 10})
        
        reports = report_generator.get_all_reports()
        assert len(reports) == 3
        assert reports[0]["report_type"] == "ingestion"
        assert reports[1]["report_type"] == "split"
        assert reports[2]["report_type"] == "lineage"
