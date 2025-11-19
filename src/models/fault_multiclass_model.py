# src/models/fault_multiclass_model.py
from pathlib import Path
from typing import Tuple, Dict

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import FAULT_MULTICLASS_MODEL_PATH
from src.preprocessing.features import get_feature_columns


def split_multiclass_target(df: pd.DataFrame, label_col: str = "FailureMode"):
    """
    X = all features (drop failure flags + FailureMode)
    y = FailureMode multi-class label
    """
    drop_cols = ["Machine failure", "TWF", "HDF", "PWF", "OSF", "RNF", label_col]
    X = df.drop(columns=drop_cols, errors="ignore")
    y = df[label_col].astype("category")
    return X, y


def train_multiclass_fault_classifier(df: pd.DataFrame) -> Tuple[ImbPipeline, Dict]:
    """
    Train a RandomForest multi-class classifier for FailureMode.
    Uses SMOTE to handle class imbalance (normal >> failure types).
    """
    X_all, y_all = split_multiclass_target(df, label_col="FailureMode")

    # We reuse numeric/categorical feature detection from get_feature_columns:
    # but it expects a df with failure columns still there, so we call it
    # on the original df and map back to X_all's columns.
    _, num_cols_all, cat_cols_all = get_feature_columns(df)

    # Intersect with actual X_all columns (in case we dropped some)
    num_cols = [c for c in num_cols_all if c in X_all.columns]
    cat_cols = [c for c in cat_cols_all if c in X_all.columns]

    X_train, X_test, y_train, y_test = train_test_split(
        X_all,
        y_all,
        test_size=0.2,
        random_state=42,
        stratify=y_all,
    )

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(drop="first"), cat_cols),
        ]
    )

    rf = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        n_jobs=-1,
        random_state=42,
        class_weight=None,  # SMOTE will balance data
    )

    pipe = ImbPipeline(
        steps=[
            ("preprocess", pre),
            ("smote", SMOTE(random_state=42, sampling_strategy="not majority")),
            ("model", rf),
        ]
    )

    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)

    report = classification_report(y_test, y_pred, output_dict=True)
    metrics = {"classification_report": report}

    return pipe, metrics


def save_multiclass_fault_model(model: ImbPipeline, path: Path = FAULT_MULTICLASS_MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_multiclass_fault_model(path: Path = FAULT_MULTICLASS_MODEL_PATH) -> ImbPipeline:
    return joblib.load(path)


def predict_failure_mode(model: ImbPipeline, X: pd.DataFrame) -> np.ndarray:
    """
    Predict the FailureMode class label for each row.
    """
    return model.predict(X)


def predict_failure_mode_proba(model: ImbPipeline, X: pd.DataFrame) -> np.ndarray:
    """
    Predict class probabilities for each FailureMode.
    Returns array of shape (n_samples, n_classes).
    """
    return model.predict_proba(X)
