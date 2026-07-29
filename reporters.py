"""
ProtonAI - Reporters Module
وحدة توليد التقارير الاحترافية
تجمع المعلومات من جميع الوحدات وتقدمها في تقارير منظمة
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger("ProtonAI.Reporters")


@dataclass
class ReportSection:
    """قسم في التقرير"""
    title: str
    content: Any
    section_type: str = "text"  # text, table, stats


class ReportGenerator:
    """
    مولد التقارير الاحترافي لمنصة ProtonAI.
    يدعم توليد تقارير بصيغ JSON و Markdown.
    """

    def __init__(self, report_dir: Optional[str | Path] = None):
        """
        تهيئة مولد التقارير.
        
        Args:
            report_dir: مسار المجلد لحفظ التقارير (اختياري)
        """
        self.report_dir = Path(report_dir) if report_dir else None
        self.reports: List[Dict[str, Any]] = []
        
        if self.report_dir:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"تم تهيئة مولد التقارير، المسار: {self.report_dir}")
        else:
            logger.info("تم تهيئة مولد التقارير (بدون حفظ تلقائي)")

    def generate_ingestion_report(self, ingestion_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        توليد تقرير استيعاب البيانات.
        
        Args:
            ingestion_stats: إحصائيات من وحدة ingestion.py
            
        Returns:
            Dict[str, Any]: تقرير الاستيعاب
        """
        report = {
            "report_type": "ingestion",
            "timestamp": datetime.now().isoformat(),
            "title": "تقرير استيعاب البيانات",
            "sections": [
                {
                    "title": "الإحصائيات العامة",
                    "type": "stats",
                    "data": ingestion_stats
                }
            ]
        }
        
        self.reports.append(report)
        logger.info(f"تم توليد تقرير الاستيعاب: {ingestion_stats.get('total_processed', 0)} سجل")
        
        return report

    def generate_split_report(self, split_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        توليد تقرير تقسيم البيانات.
        
        Args:
            split_summary: ملخص من وحدة split.py
            
        Returns:
            Dict[str, Any]: تقرير التقسيم
        """
        report = {
            "report_type": "split",
            "timestamp": datetime.now().isoformat(),
            "title": "تقرير تقسيم البيانات",
            "sections": [
                {
                    "title": "ملخص التقسيم",
                    "type": "stats",
                    "data": split_summary
                }
            ]
        }
        
        self.reports.append(report)
        logger.info(f"تم توليد تقرير التقسيم: {split_summary.get('total_samples', 0)} عينة")
        
        return report

    def generate_lineage_report(self, lineage_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        توليد تقرير تتبع النسب.
        
        Args:
            lineage_summary: ملخص من وحدة lineage.py
            
        Returns:
            Dict[str, Any]: تقرير تتبع النسب
        """
        report = {
            "report_type": "lineage",
            "timestamp": datetime.now().isoformat(),
            "title": "تقرير تتبع النسب",
            "sections": [
                {
                    "title": "ملخص التتبع",
                    "type": "stats",
                    "data": lineage_summary
                }
            ]
        }
        
        self.reports.append(report)
        logger.info(f"تم توليد تقرير التتبع: {lineage_summary.get('total_transformations', 0)} تحوّل")
        
        return report

    def generate_comprehensive_report(
        self,
        ingestion_stats: Optional[Dict[str, Any]] = None,
        split_summary: Optional[Dict[str, Any]] = None,
        lineage_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        توليد تقرير شامل يجمع كل المعلومات.
        
        Args:
            ingestion_stats: إحصائيات الاستيعاب
            split_summary: ملخص التقسيم
            lineage_summary: ملخص التتبع
            
        Returns:
            Dict[str, Any]: التقرير الشامل
        """
        report = {
            "report_type": "comprehensive",
            "timestamp": datetime.now().isoformat(),
            "title": "التقرير الشامل لمنصة ProtonAI",
            "sections": []
        }
        
        if ingestion_stats:
            report["sections"].append({
                "title": "استيعاب البيانات",
                "type": "stats",
                "data": ingestion_stats
            })
        
        if split_summary:
            report["sections"].append({
                "title": "تقسيم البيانات",
                "type": "stats",
                "data": split_summary
            })
        
        if lineage_summary:
            report["sections"].append({
                "title": "تتبع النسب",
                "type": "stats",
                "data": lineage_summary
            })
        
        self.reports.append(report)
        logger.info("تم توليد التقرير الشامل")
        
        return report

    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """
        حفظ التقرير في ملف JSON.
        
        Args:
            report: التقرير المراد حفظه
            filename: اسم الملف (اختياري، يُنشأ تلقائياً إذا لم يُحدد)
            
        Returns:
            Path: مسار الملف المحفوظ
        """
        if not self.report_dir:
            raise ValueError("لم يتم تحديد مسار لحفظ التقارير")
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_type = report.get("report_type", "unknown")
            filename = f"{report_type}_{timestamp}.json"
        
        file_path = self.report_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"تم حفظ التقرير في: {file_path}")
        
        return file_path

    def export_to_markdown(self, report: Dict[str, Any]) -> str:
        """
        تصدير التقرير بصيغة Markdown.
        
        Args:
            report: التقرير المراد تصديره
            
        Returns:
            str: التقرير بصيغة Markdown
        """
        md_content = f"# {report.get('title', 'Report')}\n\n"
        md_content += f"**Timestamp:** {report.get('timestamp', 'N/A')}\n\n"
        md_content += "---\n\n"
        
        for section in report.get("sections", []):
            md_content += f"## {section.get('title', 'Section')}\n\n"
            
            if section.get("type") == "stats":
                data = section.get("data", {})
                for key, value in data.items():
                    md_content += f"- **{key}:** {value}\n"
            else:
                md_content += f"{section.get('content', '')}\n"
            
            md_content += "\n"
        
        return md_content

    def save_markdown_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """
        حفظ التقرير بصيغة Markdown.
        
        Args:
            report: التقرير المراد حفظه
            filename: اسم الملف (اختياري)
            
        Returns:
            Path: مسار الملف المحفوظ
        """
        if not self.report_dir:
            raise ValueError("لم يتم تحديد مسار لحفظ التقارير")
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_type = report.get("report_type", "unknown")
            filename = f"{report_type}_{timestamp}.md"
        
        file_path = self.report_dir / filename
        md_content = self.export_to_markdown(report)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"تم حفظ تقرير Markdown في: {file_path}")
        
        return file_path

    def get_all_reports(self) -> List[Dict[str, Any]]:
        """الحصول على جميع التقارير المولدة"""
        return self.reports

    def get_last_report(self) -> Optional[Dict[str, Any]]:
        """الحصول على آخر تقرير"""
        if not self.reports:
            return None
        return self.reports[-1]

    def clear_reports(self) -> None:
        """مسح جميع التقارير"""
        self.reports.clear()
        logger.info("تم مسح جميع التقارير")
