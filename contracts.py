"""
ProtonAI Data Contracts
Defines clinical schema, validation rules, and business logic constraints.
"""

from enum import Enum
from typing import Optional, List, Any


class ValidationLevel(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class DataType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    CATEGORICAL = "categorical"


class FieldConstraint:
    """Clinical field definition with validation rules"""

    def __init__(
        self,
        field_name: str,
        data_type: DataType,
        required: bool = True,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allowed_values: Optional[List[Any]] = None,
        validation_level: ValidationLevel = ValidationLevel.CRITICAL,
        clinical_description: str = ""
    ):
        self.field_name = field_name
        self.data_type = data_type
        self.required = required
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = allowed_values
        self.validation_level = validation_level
        self.clinical_description = clinical_description

    def validate(self, value: Any) -> List[dict]:
        """Validate a single value against this constraint."""
        import pandas as pd
        import numpy as np

        errors = []

        # Check missing
        if pd.isna(value) or value is None or (isinstance(value, float) and np.isnan(value)):
            if self.required:
                errors.append({
                    "field": self.field_name,
                    "level": self.validation_level.value,
                    "message": f"Required field '{self.field_name}' is missing",
                    "value": None
                })
            return errors

        # Type check
        type_valid = self._check_type(value)
        if not type_valid:
            errors.append({
                "field": self.field_name,
                "level": ValidationLevel.CRITICAL.value,
                "message": f"Invalid type for '{self.field_name}': expected {self.data_type.value}",
                "value": str(value)[:50]
            })
            return errors

        # Range checks
        if self.min_value is not None and value < self.min_value:
            errors.append({
                "field": self.field_name,
                "level": self.validation_level.value,
                "message": f"Value {value} below minimum {self.min_value}",
                "value": value
            })

        if self.max_value is not None and value > self.max_value:
            errors.append({
                "field": self.field_name,
                "level": self.validation_level.value,
                "message": f"Value {value} exceeds maximum {self.max_value}",
                "value": value
            })

        # Allowed values check
        if self.allowed_values is not None and value not in self.allowed_values:
            errors.append({
                "field": self.field_name,
                "level": self.validation_level.value,
                "message": f"Disallowed value: '{value}'. Allowed: {self.allowed_values}",
                "value": value
            })

        return errors

    def _check_type(self, value: Any) -> bool:
        import numpy as np

        if self.data_type == DataType.STRING:
            return isinstance(value, (str, np.str_))
        elif self.data_type == DataType.INTEGER:
            return isinstance(value, (int, np.integer)) and not isinstance(value, bool)
        elif self.data_type == DataType.FLOAT:
            return isinstance(value, (float, np.floating, int, np.integer))
        elif self.data_type == DataType.BOOLEAN:
            return isinstance(value, (bool, np.bool_))
        elif self.data_type == DataType.DATETIME:
            import pandas as pd
            try:
                pd.to_datetime(value)
                return True
            except:
                return False
        elif self.data_type == DataType.CATEGORICAL:
            return isinstance(value, (str, int, float, np.number))
        return False


class ProtonDataContract:
    """Master data contract for ProtonAI clinical data."""

    # Patient demographics
    PATIENT_ID = FieldConstraint("patient_id", DataType.STRING, True, clinical_description="De-identified patient ID")
    STUDY_ID = FieldConstraint("study_id", DataType.STRING, True, clinical_description="Study/session ID")
    AGE = FieldConstraint("age", DataType.INTEGER, True, min_value=0, max_value=120, clinical_description="Patient age in years")
    SEX = FieldConstraint("sex", DataType.CATEGORICAL, True, allowed_values=["M", "F", "Male", "Female"], clinical_description="Patient sex")

    # Tumor
    TUMOR_SITE = FieldConstraint("tumor_site", DataType.CATEGORICAL, True,
        allowed_values=["brain", "head_neck", "lung", "liver", "prostate", "breast", "spine", "pelvis", "abdomen", "extremity", "other"],
        clinical_description="Primary tumor anatomical site")
    TUMOR_VOLUME_ML = FieldConstraint("tumor_volume_ml", DataType.FLOAT, True, min_value=0.001, max_value=5000.0,
        validation_level=ValidationLevel.WARNING, clinical_description="Tumor volume in mL")
    TUMOR_STAGE = FieldConstraint("tumor_stage", DataType.CATEGORICAL, False,
        allowed_values=["I", "II", "III", "IV", "T1", "T2", "T3", "T4"], clinical_description="Tumor stage")
    HISTOLOGY = FieldConstraint("histology", DataType.STRING, False, clinical_description="Histological type")

    # Dose
    DOSE_GY = FieldConstraint("dose_gy", DataType.FLOAT, True, min_value=0.1, max_value=100.0, clinical_description="Total prescribed dose in Gy")
    FRACTION_COUNT = FieldConstraint("fraction_count", DataType.INTEGER, True, min_value=1, max_value=50, clinical_description="Number of fractions")
    DOSE_PER_FRACTION = FieldConstraint("dose_per_fraction", DataType.FLOAT, False, min_value=0.1, max_value=30.0,
        validation_level=ValidationLevel.WARNING, clinical_description="Dose per fraction")

    # Imaging
    CT_TIMESTAMP = FieldConstraint("ct_timestamp", DataType.DATETIME, True, clinical_description="CT scan timestamp")
    VOXEL_SIZE_MM = FieldConstraint("voxel_size_mm", DataType.FLOAT, False, min_value=0.1, max_value=10.0, clinical_description="Voxel size in mm")

    # Outcomes
    LOCAL_CONTROL = FieldConstraint("local_control", DataType.BOOLEAN, False, clinical_description="Local control achieved")
    TOXICITY_GRADE = FieldConstraint("toxicity_grade", DataType.INTEGER, False, min_value=0, max_value=5, clinical_description="Toxicity grade CTCAE 0-5")
    SURVIVAL_MONTHS = FieldConstraint("survival_months", DataType.FLOAT, False, min_value=0, max_value=600, clinical_description="Survival in months")

    # Proton specific
    BEAM_ENERGY_MEV = FieldConstraint("beam_energy_mev", DataType.FLOAT, False, min_value=50, max_value=250, clinical_description="Proton beam energy in MeV")
    RBE = FieldConstraint("rbe", DataType.FLOAT, False, min_value=1.0, max_value=1.5,
        validation_level=ValidationLevel.WARNING, clinical_description="Relative Biological Effectiveness")

    @classmethod
    def get_all_constraints(cls) -> dict:
        """Get all field constraints keyed by field_name."""
        return {
            value.field_name: value
            for value in cls.__dict__.values()
            if isinstance(value, FieldConstraint)
        }

    @classmethod
    def get_required_fields(cls) -> List[str]:
        return [c.field_name for c in cls.get_all_constraints().values() if c.required]

    @classmethod
    def get_target_fields(cls) -> List[str]:
        return ["local_control", "toxicity_grade", "survival_months"]

    @classmethod
    def get_feature_fields(cls) -> List[str]:
        all_fields = set(cls.get_all_constraints().keys())
        return list(all_fields - set(cls.get_target_fields()))
