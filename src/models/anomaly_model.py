# src/models/anomaly_model.py
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import ANOMALY_MODEL_PATH
from src.preprocessing.features import get_feature_columns


def train_anomaly_model(df: pd.DataFrame) -> Pipeline:
    """
    Train IsolationForest anomaly detector on feature set (unsupervised).
    Expects processed dataframe (from ETL).
    """
    X_raw, num_cols, cat_cols = get_feature_columns(df)

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(drop="first"), cat_cols),
        ]
    )

    iso = IsolationForest(
        n_estimators=200,
        contamination=0.03,  # approx failure rate
        random_state=42,
    )

    pipe = Pipeline(
        steps=[
            ("preprocess", pre),
            ("clf", iso),
        ]
    )

    pipe.fit(X_raw)
    return pipe


def save_anomaly_model(model: Pipeline, path: Path = ANOMALY_MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_anomaly_model(path: Path = ANOMALY_MODEL_PATH) -> Pipeline:
    return joblib.load(path)


def compute_anomaly_score(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """
    Higher score = more anomalous.
    """
    iso = model.named_steps["clf"]
    # IsolationForest score_samples: higher = more normal, so invert
    scores = -iso.score_samples(model.named_steps["preprocess"].transform(X))
    return scores
