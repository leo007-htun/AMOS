# src/preprocessing/features.py
import pandas as pd


FAILURE_COLS = ["Machine failure", "TWF", "HDF", "PWF", "OSF", "RNF"]
CAT_COLS = ["Type"]


def split_features_target(df: pd.DataFrame, target_col: str = "Machine failure"):
    """
    Split processed dataframe into X, y for supervised training.
    Drops all failure indicator columns from X.
    """
    X = df.drop(columns=FAILURE_COLS, errors="ignore")
    y = df[target_col].astype(int)
    return X, y


def get_feature_columns(df: pd.DataFrame):
    """
    Get feature, numeric, and categorical columns after ETL.
    """
    X = df.drop(columns=FAILURE_COLS, errors="ignore")
    cat_cols = [c for c in X.columns if c in CAT_COLS]
    num_cols = [c for c in X.columns if c not in cat_cols]
    return X, num_cols, cat_cols


def build_single_row_feature_df(row: pd.Series) -> pd.DataFrame:
    """
    Convert a raw/processed row (Series) into a single-row DataFrame
    with the same feature columns expected by the trained models.
    """
    df = row.to_frame().T  # single-row DataFrame
    # Ensure failure columns are present for drop, even if NaN
    for c in FAILURE_COLS:
        if c not in df.columns:
            df[c] = 0
    X = df.drop(columns=FAILURE_COLS, errors="ignore")
    return X
