"""
ProtonAI - Data Ingestion Pipeline
Production-ready data ingestion with validation and lineage tracking.
"""

import pandas as pd
import numpy as np
import hashlib
from pathlib import Path
from typing import Union, Dict, Any

from .contracts import ProtonDataContract
from .validators import CrossFieldValidator
from .normalizers import ColumnNormalizer
from .reporters import ReportGenerator
from .lineage import DataLineageTracker


class CompletenessChecker:
    @staticmethod
    def check_completeness(df, required_cols):
        total = len(df)
        results = {"total_rows": total, "fields": {}}
        for col in required_cols:
            if col not in df.columns:
                results["fields"][col] = {"present": False, "missing_count": total, "missing_pct": 100.0, "status": "missing_column"}
            else:
                missing = df[col].isna().sum()
                pct = (missing / total) * 100
                status = "complete" if missing == 0 else "acceptable" if pct < 5 else "critical" if pct > 20 else "warning"
                results["fields"][col] = {"present": True, "missing_count": int(missing), "missing_pct": round(pct, 2), "status": status}
        return results


class OutlierDetector:
    from scipy import stats

    @staticmethod
    def detect_all(df, numeric_cols):
        from scipy import stats
        results = {}
        for col in numeric_cols:
            if col not in df.columns or len(df[col].dropna()) < 10:
                continue
            series = df[col]
            Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
            IQR = Q3 - Q1
            iqr_mask = (series < (Q1 - 1.5*IQR)) | (series > (Q3 + 1.5*IQR))

            z = np.abs(stats.zscore(series.dropna()))
            z_mask = pd.Series(False, index=series.index)
            z_mask.loc[series.dropna().index] = z > 3.0

            median = series.median()
            mad = np.median(np.abs(series - median))
            if mad == 0:
                mz_mask = pd.Series(False, index=series.index)
            else:
                mz = 0.6745 * (series - median) / mad
                mz_mask = np.abs(mz) > 3.5

            results[col] = {
                "iqr": iqr_mask,
                "zscore": z_mask,
                "modified_zscore": mz_mask
            }
        return results


class ProtonIngestionPipeline:
    """Main ingestion pipeline for ProtonAI clinical data."""

    def __init__(self, contract=None, output_dir="./protonai_output", pipeline_version="1.0.0"):
        self.contract = contract or ProtonDataContract
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lineage = DataLineageTracker()
        self.reporter = ReportGenerator(pipeline_version)
        self.version = pipeline_version
        for subdir in ["data", "reports/json", "reports/markdown", "lineage"]:
            (self.output_dir / subdir).mkdir(parents=True, exist_ok=True)

    def run(self, input_path: Union[str, pd.DataFrame]) -> Dict[str, Any]:
        print(f"🚀 ProtonAI Ingestion Pipeline v{self.version}")
        print("=" * 50)

        raw_df = self._load_data(input_path)
        self.lineage.log_step("load_data", (0,0), raw_df.shape, records_affected=len(raw_df))
        print(f"📥 Loaded {len(raw_df)} rows, {len(raw_df.columns)} columns")

        norm_df = ColumnNormalizer.normalize(raw_df)
        self.lineage.log_step("normalize_columns", raw_df.shape, norm_df.shape,
                              parameters={"original": list(raw_df.columns), "normalized": list(norm_df.columns)})
        print(f"🔤 Columns normalized: {list(norm_df.columns)}")

        print("🔍 Validating raw values BEFORE type coercion...")
        validation = self._validate_contract(norm_df)
        print(f"   Found {len(validation.get('errors', []))} validation errors")
        print(f"   - Critical: {validation.get('critical_count', 0)}")
        print(f"   - Warnings: {validation.get('warning_count', 0)}")

        typed_df = self._coerce_types(norm_df)
        self.lineage.log_step("coerce_types", norm_df.shape, typed_df.shape)

        completeness = CompletenessChecker.check_completeness(typed_df, self.contract.get_required_fields())
        print(f"📊 Completeness: {self.reporter._calc_completeness(completeness):.1f}%")

        numeric_cols = [c for c in typed_df.columns if typed_df[c].dtype in ['int64', 'float64', 'Int64']]
        outliers = OutlierDetector.detect_all(typed_df, numeric_cols)
        total_outliers = sum(m["iqr"].sum() for m in outliers.values())
        print(f"🔍 Outliers detected: {int(total_outliers)}")

        cross_errors = []
        cross_errors.extend(CrossFieldValidator.validate_dose_fractions(typed_df))
        cross_errors.extend(CrossFieldValidator.validate_age_tumor_consistency(typed_df))
        print(f"🔗 Cross-field issues: {len(cross_errors)}")

        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.output_dir / "reports" / "json" / f"report_{ts}.json"
        md_path = self.output_dir / "reports" / "markdown" / f"report_{ts}.md"
        self.reporter.generate_json_report(validation, outliers, cross_errors, completeness, str(json_path))
        self.reporter.generate_markdown_report(validation, outliers, cross_errors, completeness, str(md_path))

        clean_path = self.output_dir / "data" / "prepared.csv"
        typed_df.to_csv(clean_path, index=False, encoding='utf-8')
        self.lineage.log_step("save_clean_data", typed_df.shape, typed_df.shape, parameters={"path": str(clean_path)})
        print(f"💾 Clean data: {clean_path}")

        lineage_path = self.output_dir / "lineage" / f"lineage_{self.lineage.run_id}.json"
        self.lineage.save(str(lineage_path))
        print(f"📋 Lineage: {lineage_path}")

        summary = {
            "status": "success" if validation.get("critical_count", 0) == 0 else "failed",
            "run_id": self.lineage.run_id,
            "input_records": len(raw_df),
            "output_records": len(typed_df),
            "columns": list(typed_df.columns),
            "validation": {"total_errors": len(validation.get("errors", [])), "critical": validation.get("critical_count", 0), "warnings": validation.get("warning_count", 0)},
            "completeness_score": self.reporter._calc_completeness(completeness),
            "outliers": int(total_outliers),
            "cross_field_issues": len(cross_errors),
            "files": {"clean_data": str(clean_path), "json_report": str(json_path), "markdown_report": str(md_path), "lineage": str(lineage_path)}
        }

        print("\n" + "=" * 50)
        print(f"✨ Pipeline complete! Run ID: {self.lineage.run_id} | Status: {summary['status'].upper()}")
        return summary

    def _load_data(self, input_path):
        if isinstance(input_path, pd.DataFrame):
            return input_path.copy()
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")
        file_hash = hashlib.md5(path.read_bytes()).hexdigest()
        if path.suffix.lower() == '.csv':
            df = pd.read_csv(input_path, encoding='utf-8')
        elif path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(input_path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")
        self.lineage.log_source(str(path), file_hash, len(df), list(df.columns))
        return df

    def _coerce_types(self, df):
        df = df.copy()
        constraints = self.contract.get_all_constraints()
        for col, constraint in constraints.items():
            if col not in df.columns:
                continue
            try:
                if constraint.data_type.value == "integer":
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                elif constraint.data_type.value == "float":
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif constraint.data_type.value == "boolean":
                    df[col] = df[col].map({True: True, False: False, 1: True, 0: False, 'yes': True, 'no': False, 'true': True, 'false': False})
                elif constraint.data_type.value == "datetime":
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                elif constraint.data_type.value in ["categorical", "string"]:
                    df[col] = df[col].astype(str).replace('nan', np.nan).replace('None', np.nan)
            except Exception as e:
                print(f"⚠️ Type coercion warning for {col}: {e}")
        return df

    def _validate_contract(self, df):
        constraints = self.contract.get_all_constraints()
        all_errors = []
        critical_count = 0
        warning_count = 0

        for col, constraint in constraints.items():
            if col not in df.columns:
                if constraint.required:
                    all_errors.append({"row": "all", "field": col, "level": "critical", "message": f"Required column '{col}' missing", "value": None})
                    critical_count += 1
                continue

            for idx, value in df[col].items():
                if pd.isna(value) and not constraint.required:
                    continue
                for error in constraint.validate(value):
                    error["row"] = int(idx)
                    all_errors.append(error)
                    if error["level"] == "critical":
                        critical_count += 1
                    else:
                        warning_count += 1

        return {"errors": all_errors, "total_count": len(all_errors), "critical_count": critical_count, "warning_count": warning_count}
