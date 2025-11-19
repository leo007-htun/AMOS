# scripts/train_fault.py
import pandas as pd

from src.preprocessing.etl import create_processed_dataset
from src.models.fault_model import train_fault_classifier, save_fault_model
from src.config import PROCESSED_DATA_PATH, FAULT_MODEL_PATH


def main():
    path = create_processed_dataset(force=False)
    print(f"Using processed data at: {path}")

    df = pd.read_csv(PROCESSED_DATA_PATH)
    model, metrics = train_fault_classifier(df)
    save_fault_model(model)

    print(f"Fault classifier saved to: {FAULT_MODEL_PATH}")
    print("ROC-AUC:", metrics["roc_auc"])
    # If you want more detail:
    # print(metrics["classification_report"])


if __name__ == "__main__":
    main()
