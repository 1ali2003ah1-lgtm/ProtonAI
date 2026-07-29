"""
ProtonAI - Test Pipeline
اختبار خط المعالجة الكامل (End-to-End)
"""

import pytest
import tempfile
from pathlib import Path
from pipeline import run_proton_ai_pipeline


class TestProtonAIPipeline:
    """اختبارات خط المعالجة المتكامل"""
    
    def test_pipeline_runs_successfully(self):
        """اختبار أن الخط يعمل من البداية للنهاية"""
        with tempfile.TemporaryDirectory() as tmpdirname:
            result = run_proton_ai_pipeline(output_dir=tmpdirname)
            assert result["status"] == "success"
            assert "report" in result
            
    def test_pipeline_generates_report_file(self):
        """اختبار أن الخط ينتج ملف التقرير"""
        with tempfile.TemporaryDirectory() as tmpdirname:
            run_proton_ai_pipeline(output_dir=tmpdirname)
            report_path = Path(tmpdirname) / "final_pipeline_report.json"
            assert report_path.exists()
            
    def test_pipeline_saves_model(self):
        """اختبار أن الخط يحفظ النموذج المدرب"""
        with tempfile.TemporaryDirectory() as tmpdirname:
            run_proton_ai_pipeline(output_dir=tmpdirname)
            model_path = Path(tmpdirname) / "baseline_model.json"
            assert model_path.exists()
            
    def test_pipeline_report_contains_metrics(self):
        """اختبار أن التقرير يحتوي على مقاييس النموذج"""
        with tempfile.TemporaryDirectory() as tmpdirname:
            result = run_proton_ai_pipeline(output_dir=tmpdirname)
            report = result["report"]
            assert "model_metrics" in report
            assert "mse" in report["model_metrics"]
            assert "r2_score" in report["model_metrics"]
