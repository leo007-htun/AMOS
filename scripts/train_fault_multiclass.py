# scripts/train_fault_multiclass.py
"""
Train multiclass fault classifier

This script trains a RandomForest classifier to identify the specific
type of failure mode (NORMAL, TWF, HDF, PWF, OSF, RNF) based on sensor data.
"""

import pandas as pd

from src.preprocessing.etl import create_processed_dataset
from src.models.fault_multiclass_model import (
    train_multiclass_fault_classifier,
    save_multiclass_fault_model,
)
from src.config import PROCESSED_DATA_PATH, FAULT_MULTICLASS_MODEL_PATH


def main():
    print("=" * 60)
    print("Training Multiclass Fault Classifier")
    print("=" * 60)

    # Ensure processed data exists
    path = create_processed_dataset(force=False)
    print(f"\nUsing processed data at: {path}")

    # Load data
    df = pd.read_csv(PROCESSED_DATA_PATH)
    print(f"Loaded {len(df)} rows")

    # Show failure mode distribution
    print("\nFailure Mode Distribution:")
    print(df["FailureMode"].value_counts())
    print()

    # Train model
    print("Training multiclass fault classifier...")
    print("This may take a few minutes...\n")

    model, metrics = train_multiclass_fault_classifier(df)

    # Save model
    save_multiclass_fault_model(model)
    print(f"\n✓ Multiclass fault model saved to: {FAULT_MULTICLASS_MODEL_PATH}")

    # Display metrics
    print("\n" + "=" * 60)
    print("Classification Report:")
    print("=" * 60)

    report = metrics["classification_report"]

    # Print per-class metrics
    for class_name, class_metrics in report.items():
        if class_name in ["accuracy", "macro avg", "weighted avg"]:
            continue

        if isinstance(class_metrics, dict):
            precision = class_metrics.get("precision", 0)
            recall = class_metrics.get("recall", 0)
            f1 = class_metrics.get("f1-score", 0)
            support = class_metrics.get("support", 0)

            print(f"\n{class_name}:")
            print(f"  Precision: {precision:.3f}")
            print(f"  Recall:    {recall:.3f}")
            print(f"  F1-Score:  {f1:.3f}")
            print(f"  Support:   {support}")

    # Print overall metrics
    print("\n" + "-" * 60)
    print("Overall Metrics:")
    print(f"  Accuracy: {report.get('accuracy', 0):.3f}")

    if "weighted avg" in report:
        weighted = report["weighted avg"]
        print(f"  Weighted Avg F1: {weighted.get('f1-score', 0):.3f}")

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
