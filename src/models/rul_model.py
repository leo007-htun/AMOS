# src/models/rul_model.py
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import RUL_MODEL_PATH
from src.preprocessing.features import get_feature_columns


def build_rul_target(df: pd.DataFrame) -> pd.Series:
    """
    Simple RUL proxy: (max tool wear - current tool wear).
    """
    max_wear = df["Tool wear [min]"].max()
    return max_wear - df["Tool wear [min]"]


def train_rul_regressor(df: pd.DataFrame) -> Tuple[Pipeline, dict]:
    """
    Train a RandomForest regressor to predict RUL proxy.
    Returns pipeline and metrics dict.
    """
    y = build_rul_target(df)
    X_raw, num_cols, cat_cols = get_feature_columns(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X_raw,
        y,
        test_size=0.2,
        random_state=42,
    )

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(drop="first"), cat_cols),
        ]
    )

    rf = RandomForestRegressor(
        n_estimators=300,
        n_jobs=-1,
        random_state=42,
    )

    pipe = Pipeline(
        steps=[
            ("preprocess", pre),
            ("model", rf),
        ]
    )

    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    metrics = {"mae": mae, "r2": r2}
    return pipe, metrics


def save_rul_model(model: Pipeline, path: Path = RUL_MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_rul_model(path: Path = RUL_MODEL_PATH) -> Pipeline:
    return joblib.load(path)


def predict_rul(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    return model.predict(X)
