"""
ProtonAI - Data Lineage Tracker
Tracks data provenance and audit trail.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path


class DataLineageTracker:
    """Tracks every step of the data pipeline for audit and reproducibility."""

    def __init__(self, run_id=None):
        self.run_id = run_id or hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:12]
        self.steps = []
        self.start_time = datetime.now().isoformat()

    def log_step(self, step_name, input_shape, output_shape, parameters=None, records_affected=0):
        self.steps.append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "input_shape": input_shape,
            "output_shape": output_shape,
            "records_affected": records_affected,
            "parameters": parameters or {}
        })

    def log_source(self, file_path, file_hash, record_count, columns):
        self.steps.insert(0, {
            "step": "data_source",
            "timestamp": self.start_time,
            "file_path": file_path,
            "file_hash": file_hash,
            "record_count": record_count,
            "columns": columns
        })

    def save(self, output_path):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "run_id": self.run_id,
                "start_time": self.start_time,
                "end_time": datetime.now().isoformat(),
                "steps": self.steps
            }, f, indent=2, ensure_ascii=False)
