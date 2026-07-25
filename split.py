"""
ProtonAI - Clinical Data Splitter
Stratified splitting with clinical considerations.
"""

import pandas as pd
from typing import Dict
from sklearn.model_selection import train_test_split


class ClinicalSplitter:
    """Splits data respecting patient groups and clinical stratification."""

    def __init__(self, random_state=42):
        self.random_state = random_state

    def create_stratification_key(self, df: pd.DataFrame) -> pd.Series:
        keys = []
        if "tumor_site" in df.columns:
            keys.append(df["tumor_site"].fillna("unknown").astype(str))
        if "age" in df.columns:
            age_bins = pd.cut(df["age"], bins=[0, 18, 40, 60, 80, 120], 
                            labels=["child", "young", "middle", "senior", "elderly"])
            keys.append(age_bins.astype(str))
        if not keys:
            return pd.Series(["all"] * len(df))

        strat_key = keys[0]
        for k in keys[1:]:
            strat_key = strat_key + "_" + k

        vc = strat_key.value_counts()
        rare = vc[vc < 5].index
        return strat_key.replace(rare, "rare_combination")

    def split(self, df: pd.DataFrame, group_col="patient_id", 
              train_ratio=0.7, val_ratio=0.15, test_ratio=0.15) -> Dict[str, pd.DataFrame]:
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Ratios must sum to 1.0"

        df = df.copy()
        strat_key = self.create_stratification_key(df)

        if group_col not in df.columns:
            df[group_col] = range(len(df))

        groups = df[group_col].unique()
        group_strat = strat_key.groupby(df[group_col]).first()

        train_groups, temp_groups = train_test_split(
            groups, test_size=(val_ratio + test_ratio), 
            stratify=group_strat[groups], random_state=self.random_state
        )

        val_test_mask = df[group_col].isin(temp_groups)
        val_test_groups = df.loc[val_test_mask, group_col].unique()
        val_test_strat = strat_key[val_test_mask].groupby(df.loc[val_test_mask, group_col]).first()

        val_adjusted = val_ratio / (val_ratio + test_ratio)
        val_groups, test_groups = train_test_split(
            val_test_groups, test_size=(1 - val_adjusted),
            stratify=val_test_strat[val_test_groups], random_state=self.random_state
        )

        train_df = df[df[group_col].isin(train_groups)].copy()
        val_df = df[df[group_col].isin(val_groups)].copy()
        test_df = df[df[group_col].isin(test_groups)].copy()

        assert len(set(train_df[group_col]) & set(val_df[group_col])) == 0
        assert len(set(train_df[group_col]) & set(test_df[group_col])) == 0
        assert len(set(val_df[group_col]) & set(test_df[group_col])) == 0

        print(f"📊 Clinical Split: Train={len(train_df)} ({len(train_df)/len(df):.0%}) | Val={len(val_df)} ({len(val_df)/len(df):.0%}) | Test={len(test_df)} ({len(test_df)/len(df):.0%})")

        return {"train": train_df, "validation": val_df, "test": test_df}
