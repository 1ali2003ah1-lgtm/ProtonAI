"""
ProtonAI Clinical Validators
Advanced validation logic including cross-field checks.
"""

import pandas as pd
from typing import List, Dict, Any


class CrossFieldValidator:
    """Validates consistency between multiple fields."""

    @staticmethod
    def validate_dose_fractions(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Check that total dose ≈ fractions × dose_per_fraction."""
        errors = []
        if "dose_gy" not in df.columns or "fraction_count" not in df.columns:
            return errors

        for idx, row in df.iterrows():
            if pd.isna(row.get("dose_gy")) or pd.isna(row.get("fraction_count")):
                continue
            if row["fraction_count"] == 0:
                continue

            expected = row["dose_gy"] / row["fraction_count"]

            if "dose_per_fraction" in df.columns and not pd.isna(row.get("dose_per_fraction")):
                actual = row["dose_per_fraction"]
                deviation = abs(expected - actual) / expected if expected > 0 else 0

                if deviation > 0.1:
                    errors.append({
                        "row": int(idx),
                        "type": "cross_field_inconsistency",
                        "message": (
                            f"Dose mismatch: total={row['dose_gy']:.2f}, "
                            f"fractions={row['fraction_count']}, "
                            f"expected_per_fraction={expected:.2f}, "
                            f"actual={actual:.2f}"
                        ),
                        "severity": "warning"
                    })
        return errors

    @staticmethod
    def validate_age_tumor_consistency(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Check clinical consistency between age and tumor site."""
        errors = []
        if "age" not in df.columns or "tumor_site" not in df.columns:
            return errors

        for idx, row in df.iterrows():
            age, site = row.get("age"), row.get("tumor_site")
            if pd.isna(age) or pd.isna(site):
                continue

            if site == "prostate" and age < 30:
                errors.append({
                    "row": int(idx),
                    "type": "clinical_inconsistency",
                    "message": f"Prostate tumor at age {age} is clinically rare",
                    "severity": "warning"
                })

            if site == "brain" and age < 5:
                errors.append({
                    "row": int(idx),
                    "type": "clinical_inconsistency",
                    "message": f"Brain tumor at age {age} requires additional verification",
                    "severity": "info"
                })

        return errors
