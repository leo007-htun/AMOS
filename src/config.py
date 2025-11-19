# src/config.py
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "ai4i2020.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed" / "ai4i2020_prepared.csv"
REALISTIC_STREAM_PATH = DATA_DIR / "processed" / "ai4i2020_stream_realistic.csv"
SYNTHETIC_STREAM_PATH = DATA_DIR / "examples" / "synthetic_stream.csv"

MODELS_DIR = BASE_DIR / "models"
ANOMALY_MODEL_PATH = MODELS_DIR / "anomaly" / "isolation_forest.pkl"
FAULT_BINARY_MODEL_PATH = MODELS_DIR / "fault" / "failure_classifier.pkl"
FAULT_MULTICLASS_MODEL_PATH = MODELS_DIR / "fault" / "fault_multiclass.pkl"
RUL_MODEL_PATH = MODELS_DIR / "rul" / "rul_regressor.pkl"
ENERGY_MODEL_PATH = MODELS_DIR / "energy" / "energy_forecast.pkl"

# Backward compatibility alias
FAULT_MODEL_PATH = FAULT_BINARY_MODEL_PATH

# Thresholds (you can re-tune in 05_experiments.ipynb)
FAILURE_PROBA_THRESHOLD = 0.35
ANOMALY_SCORE_THRESHOLD = 0.6  # depends on fitted IsolationForest

# Optimization parameters
MAINTENANCE_COST = 500.0  # Cost of scheduled maintenance ($)
FAILURE_COST = 5000.0  # Cost of unplanned failure ($)
DOWNTIME_COST_PER_HOUR = 1000.0  # Cost per hour of downtime ($)
RUL_SAFETY_MARGIN = 20.0  # Safety margin for RUL scheduling (minutes)

# Stream / demo settings
STREAM_SLEEP_SECONDS = 0.5  # how fast to simulate streaming
BUFFER_MAXLEN = 500  # how many rows to keep in memory buffer
