"""
ProtonAI - Column Normalizer
Unifies column names from various sources.
"""

import pandas as pd


class ColumnNormalizer:
    """Normalizes column names from Arabic/English variants to standard names."""

    COLUMN_MAP = {
        "patient_id": ["patient_id", "patientid", "pid", "patient"],
        "study_id": ["study_id", "studyid", "sid", "study"],
        "age": ["age", "patient_age"],
        "sex": ["sex", "gender", "patient_sex"],
        "tumor_site": ["tumor_site", "site", "location", "tumor_location"],
        "tumor_volume_ml": ["tumor_volume_ml", "tumor_volume", "volume", "volume_ml"],
        "tumor_stage": ["tumor_stage", "stage"],
        "histology": ["histology", "histological_type"],
        "dose_gy": ["dose_gy", "total_dose", "dose", "prescribed_dose"],
        "fraction_count": ["fraction_count", "fractions", "num_fractions"],
        "dose_per_fraction": ["dose_per_fraction", "fraction_dose"],
        "ct_timestamp": ["ct_timestamp", "ct_date", "scan_date"],
        "voxel_size_mm": ["voxel_size_mm", "voxel_size", "resolution"],
        "local_control": ["local_control", "control", "local_recurrence"],
        "toxicity_grade": ["toxicity_grade", "toxicity", "grade", "toxicity_ctcae"],
        "survival_months": ["survival_months", "survival", "os_months"],
        "beam_energy_mev": ["beam_energy_mev", "energy", "beam_energy"],
        "rbe": ["rbe", "relative_biological_effectiveness"]
    }

    @classmethod
    def normalize(cls, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {}
        used = set()
        for standard, alts in cls.COLUMN_MAP.items():
            for col in df.columns:
                col_clean = col.strip().lower().replace(" ", "_").replace("-", "_")
                if col_clean in [a.lower().replace(" ", "_").replace("-", "_") for a in alts] and standard not in used:
                    rename_map[col] = standard
                    used.add(standard)
                    break
        return df.rename(columns=rename_map)
