# scripts/train_rul.py
import pandas as pd

from src.preprocessing.etl import create_processed_dataset
from src.models.rul_model import train_rul_regressor, save_rul_model
from src.models.energy_model import train_energy_regressor, save_energy_model
from src.config import (
    PROCESSED_DATA_PATH,
    RUL_MODEL_PATH,
    ENERGY_MODEL_PATH,
)


def main():
    path = create_processed_dataset(force=False)
    print(f"Using processed data at: {path}")

    df = pd.read_csv(PROCESSED_DATA_PATH)

    rul_model, rul_metrics = train_rul_regressor(df)
    save_rul_model(rul_model)
    print(f"RUL model saved to: {RUL_MODEL_PATH}")
    print("RUL metrics:", rul_metrics)

    energy_model, energy_metrics = train_energy_regressor(df)
    save_energy_model(energy_model)
    print(f"Energy model saved to: {ENERGY_MODEL_PATH}")
    print("Energy metrics:", energy_metrics)


if __name__ == "__main__":
    main()
