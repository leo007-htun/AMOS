# scripts/train_anomaly.py
from src.preprocessing.etl import create_processed_dataset
from src.models.anomaly_model import train_anomaly_model, save_anomaly_model
from src.config import PROCESSED_DATA_PATH, ANOMALY_MODEL_PATH


def main():
    path = create_processed_dataset(force=False)
    print(f"Using processed data at: {path}")

    import pandas as pd
    df = pd.read_csv(PROCESSED_DATA_PATH)

    model = train_anomaly_model(df)
    save_anomaly_model(model)
    print(f"Anomaly model saved to: {ANOMALY_MODEL_PATH}")


if __name__ == "__main__":
    main()
