# src/models/fault_model.py
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import FAULT_MODEL_PATH
from src.preprocessing.features import split_features_target, get_feature_columns


def train_fault_classifier(df: pd.DataFrame) -> Tuple[ImbPipeline, dict]:
    """
    Train a RandomForest classifier for Machine failure with SMOTE.
    Returns the trained pipeline and a metrics dict.
    """
    X_all, y_all = split_features_target(df, target_col="Machine failure")
    _, num_cols, cat_cols = get_feature_columns(df)

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
        n_estimators=300,
        max_depth=None,
        n_jobs=-1,
        random_state=42,
        class_weight=None,  # SMOTE balances data
    )

    pipe = ImbPipeline(
        steps=[
            ("preprocess", pre),
            ("smote", SMOTE(random_state=42)),
            ("model", rf),
        ]
    )

    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred, output_dict=True)
    roc_auc = roc_auc_score(y_test, y_proba)

    metrics = {
        "classification_report": report,
        "roc_auc": roc_auc,
    }

    return pipe, metrics


def save_fault_model(model: ImbPipeline, path: Path = FAULT_MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_fault_model(path: Path = FAULT_MODEL_PATH) -> ImbPipeline:
    return joblib.load(path)


def failure_probability(model: ImbPipeline, X: pd.DataFrame) -> np.ndarray:
    """
    Returns probability of Machine failure (class 1).
    """
    proba = model.predict_proba(X)[:, 1]
    return proba
