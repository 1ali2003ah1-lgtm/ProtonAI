"""
Tests for ProtonAI data contracts and validators.
Run with: pytest tests/
"""

import pytest
import pandas as pd
import numpy as np
from protonai.contracts import ProtonDataContract, FieldConstraint, DataType, ValidationLevel
from protonai.validators import CrossFieldValidator


class TestFieldConstraint:
    def test_age_in_range(self):
        constraint = ProtonDataContract.AGE
        errors = constraint.validate(45)
        assert len(errors) == 0

    def test_age_too_high(self):
        constraint = ProtonDataContract.AGE
        errors = constraint.validate(150)
        assert len(errors) == 1
        assert errors[0]["level"] == "warning"

    def test_age_negative(self):
        constraint = ProtonDataContract.AGE
        errors = constraint.validate(-5)
        assert len(errors) == 1

    def test_missing_required_field(self):
        constraint = ProtonDataContract.PATIENT_ID
        errors = constraint.validate(None)
        assert len(errors) == 1
        assert errors[0]["level"] == "critical"

    def test_sex_allowed_values(self):
        constraint = ProtonDataContract.SEX
        errors = constraint.validate("M")
        assert len(errors) == 0

        errors = constraint.validate("Unknown")
        assert len(errors) == 1

    def test_dose_range(self):
        constraint = ProtonDataContract.DOSE_GY
        errors = constraint.validate(70.0)
        assert len(errors) == 0

        errors = constraint.validate(-5.0)
        assert len(errors) == 1
        assert "below minimum" in errors[0]["message"]


class TestCrossFieldValidator:
    def test_dose_fraction_mismatch(self):
        df = pd.DataFrame({
            "dose_gy": [60.0],
            "fraction_count": [30],
            "dose_per_fraction": [1.0]  # Should be 2.0
        })
        errors = CrossFieldValidator.validate_dose_fractions(df)
        assert len(errors) == 1
        assert "Dose mismatch" in errors[0]["message"]

    def test_dose_fraction_correct(self):
        df = pd.DataFrame({
            "dose_gy": [60.0],
            "fraction_count": [30],
            "dose_per_fraction": [2.0]
        })
        errors = CrossFieldValidator.validate_dose_fractions(df)
        assert len(errors) == 0

    def test_age_tumor_inconsistency(self):
        df = pd.DataFrame({
            "age": [25],
            "tumor_site": ["prostate"]
        })
        errors = CrossFieldValidator.validate_age_tumor_consistency(df)
        assert len(errors) == 1
        assert "clinically rare" in errors[0]["message"]


class TestProtonDataContract:
    def test_required_fields_exist(self):
        required = ProtonDataContract.get_required_fields()
        assert "patient_id" in required
        assert "age" in required
        assert "dose_gy" in required

    def test_target_fields(self):
        targets = ProtonDataContract.get_target_fields()
        assert "local_control" in targets
        assert "toxicity_grade" in targets

    def test_all_constraints_loaded(self):
        constraints = ProtonDataContract.get_all_constraints()
        assert len(constraints) >= 15
        assert "patient_id" in constraints
        assert "rbe" in constraints
