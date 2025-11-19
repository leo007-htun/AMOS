# src/preprocessing/etl.py
from pathlib import Path
import pandas as pd
import numpy as np

from src.config import RAW_DATA_PATH, PROCESSED_DATA_PATH


FAILURE_SUBCOLS = ["TWF", "HDF", "PWF", "OSF", "RNF"]


def infer_failure_mode(row) -> str:
    """
    Map Machine failure + subtype flags into a single multi-class label.

    - 'NORMAL' if Machine failure == 0
    - One of {'TWF','HDF','PWF','OSF','RNF'} if Machine failure == 1

    Note: According to dataset description, if Machine failure == 1,
    at least one failure mode flag must be active.
    """
    if row["Machine failure"] == 0:
        return "NORMAL"

    # Among the subtype flags, find which one(s) are active
    active = [c for c in FAILURE_SUBCOLS if row[c] == 1]

    if len(active) == 1:
        return active[0]
    elif len(active) > 1:
        # Multiple failures - return the first one (prioritize in order: TWF, HDF, PWF, OSF, RNF)
        # This is rare but possible in the dataset
        return active[0]
    else:
        # No active flags but Machine failure == 1 - data inconsistency, default to NORMAL
        return "NORMAL"


def create_processed_dataset(force: bool = False) -> Path:
    """
    Load raw ai4i2020.csv, apply minimal ETL + simple feature engineering,
    and save to data/processed/ai4i2020_prepared.csv.
    """
    PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    if PROCESSED_DATA_PATH.exists() and not force:
        return PROCESSED_DATA_PATH

    df_raw = pd.read_csv(RAW_DATA_PATH)

    # 1) Drop pure IDs
    df = df_raw.drop(columns=["UDI", "Product ID"])

    # 2) Basic engineered features
    df["Temp_diff"] = df["Process temperature [K]"] - df["Air temperature [K]"]
    df["Power_proxy"] = df["Rotational speed [rpm]"] * df["Torque [Nm]"]
    df["Tool_wear_norm"] = df["Tool wear [min]"] / df["Tool wear [min]"].max()

    # 3) Multi-class failure mode label
    df["FailureMode"] = df.apply(infer_failure_mode, axis=1)

    # (optional) shuffle for training convenience
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)

    # Save the shuffled version (for model training)
    df.to_csv(PROCESSED_DATA_PATH, index=False)

    # Create a separate sorted version for realistic streaming simulation
    # SINGLE PRODUCT TYPE: Keep only Type L (most common, 60% of data)
    # Real factories typically produce ONE product type per production line

    # Filter to Type L only (6000 products)
    df_single_product = df[df["Type"] == "L"].copy()

    # Sort by tool wear to simulate tool degradation over production lifecycle
    df_single_product = df_single_product.sort_values("Tool wear [min]").reset_index(drop=True)

    sorted_path = PROCESSED_DATA_PATH.parent / "ai4i2020_stream_realistic.csv"
    df_single_product.to_csv(sorted_path, index=False)
    print(f"✓ Created realistic stream: Type L only, {len(df_single_product)} products, sorted by tool wear")
    print(f"  Tool wear range: {df_single_product['Tool wear [min]'].min():.0f} → {df_single_product['Tool wear [min]'].max():.0f} minutes")

    return PROCESSED_DATA_PATH

