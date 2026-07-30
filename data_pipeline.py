"""
ProtonAI - Data Pipeline
الخط الموحد: تحميل ← عقود ← إخفاء هوية ← تقسيم ← تدريب ← تقييم
مع تسجيل كل خطوة بسجل التدقيق وتقرير شامل
"""

import random
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from dataset_loader import DatasetLoader
from dataset_contracts import DatasetContract
from generic_model import GenericModel
from anonymizer import Anonymizer
from audit import AuditTrail, AuditOutcome

logger = logging.getLogger("ProtonAI.DataPipeline")


@dataclass
class PipelineConfig:
    """إعدادات خط المعالجة"""
    feature_columns: List[str]
    target_column: str
    task: str = "auto"
    acceptance_threshold: float = 0.95
    anonymize: bool = False
    anonymizer_salt: str = "ProtonAI-pipeline-salt"
    train_ratio: float = 0.8
    random_seed: int = 42

    def __post_init__(self):
        if not self.feature_columns:
            raise ValueError("feature_columns لا يمكن أن تكون فارغة")
        if not (0 < self.train_ratio <= 1.0):
            raise ValueError("train_ratio يجب أن يكون بين 0 و 1")


@dataclass
class PipelineReport:
    """تقرير شامل لنتيجة الخط"""
    source: str = ""
    loaded: int = 0
    contract: Optional[Dict[str, Any]] = None
    anonymization: Optional[Dict[str, Any]] = None
    training: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None
    train_samples: int = 0
    test_samples: int = 0
    status: str = "pending"  # pending | success | rejected | failed
    message: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == "success"

    def summary(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "status": self.status,
            "message": self.message,
            "loaded": self.loaded,
            "train_samples": self.train_samples,
            "test_samples": self.test_samples,
            "contract": self.contract,
            "anonymization": self.anonymization,
            "evaluation": self.evaluation,
        }


class DataPipeline:
    """
    مايسترو خط المعالجة.
    يربط التحميل والعقود وإخفاء الهوية والنموذج والتدقيق بخط واحد آمن.
    """

    def __init__(
        self,
        config: PipelineConfig,
        contract: Optional[DatasetContract] = None,
        audit: Optional[AuditTrail] = None,
    ):
        self.config = config
        self.contract = contract
        self.audit = audit if audit is not None else AuditTrail()
        self.loader = DatasetLoader(config.feature_columns, config.target_column)
        self.model = GenericModel(
            config.feature_columns, config.target_column, task=config.task)
        self.anonymizer = Anonymizer(salt=config.anonymizer_salt) if config.anonymize else None

    def _split(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """تقسيم حتمي (بذرة ثابتة) إلى تدريب واختبار"""
        if self.config.train_ratio >= 1.0 or len(records) < 4:
            return list(records), []
        rng = random.Random(self.config.random_seed)
        shuffled = list(records)
        rng.shuffle(shuffled)
        n = int(len(shuffled) * self.config.train_ratio)
        return shuffled[:n], shuffled[n:]

    def run(self, path: str) -> PipelineReport:
        """تنفيذ الخط الكامل على ملف، يرجع تقريراً شاملاً"""
        report = PipelineReport(source=str(path))
        try:
            # 1) التحميل
            records = self.loader.load(path)
            report.loaded = len(records)
            self.audit.log("pipeline", "load", str(path),
                           AuditOutcome.SUCCESS, {"rows": len(records)})
            if not records:
                report.status = "failed"
                report.message = "الملف لا يحتوي بيانات"
                return report

            # 2) فحص العقود (بوابة الرفض)
            if self.contract is not None:
                cr = self.contract.validate_dataset(records, self.config.acceptance_threshold)
                report.contract = cr.summary()
                self.audit.log(
                    "pipeline", "contract_check", self.contract.name,
                    AuditOutcome.SUCCESS if cr.is_acceptable else AuditOutcome.DENIED,
                    cr.summary())
                if not cr.is_acceptable:
                    report.status = "rejected"
                    report.message = (
                        f"البيانات مرفوضة: نسبة القبول {cr.summary()['acceptance_rate']} "
                        f"أقل من العتبة المطلوبة")
                    return report

            # 3) إخفاء الهوية (اختياري)
            if self.anonymizer is not None:
                records, anon = self.anonymizer.anonymize_batch(records)
                report.anonymization = anon.summary()
                self.audit.log("pipeline", "anonymize", str(path),
                               AuditOutcome.SUCCESS, anon.summary())

            # 4) التقسيم
            train, test = self._split(records)
            report.train_samples = len(train)
            report.test_samples = len(test)

            # 5) التدريب
            train_info = self.model.fit(train)
            report.training = train_info
            self.audit.log("pipeline", "train", self.config.target_column,
                           AuditOutcome.SUCCESS, train_info)

            # 6) التقييم (على الاختبار إن وُجد، وإلا على التدريب)
            eval_data = test if test else train
            eval_info = self.model.evaluate(eval_data)
            report.evaluation = eval_info
            self.audit.log("pipeline", "evaluate", self.config.target_column,
                           AuditOutcome.SUCCESS, eval_info)

            report.status = "success"
            report.message = "اكتمل الخط بنجاح"
            logger.info(f"الخط نجح على {path}: {eval_info}")
            return report

        except Exception as e:
            report.status = "failed"
            report.message = str(e)
            self.audit.log("pipeline", "run", str(path),
                           AuditOutcome.FAILURE, {"error": str(e)})
            logger.error(f"الخط فشل على {path}: {e}")
            return report
