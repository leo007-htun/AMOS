amos/
├── data/
│   ├── raw/
│   │   └── ai4i2020.csv             # original dataset or real logs
│   ├── processed/
│   │   └── ai4i2020_prepared.csv    # cleaned/feature-engineered
│   └── examples/
│       └── synthetic_stream.csv     # if you simulate streaming
│
├── models/
│   ├── anomaly/
│   │   ├── isolation_forest.pkl
│   │   └── lstm_autoencoder.pt      # optional
│   ├── fault/
│   │   └── failure_classifier.pkl   # RandomForest/XGBoost
│   ├── rul/
│   │   └── rul_regressor.pkl        # or LSTM model
│   └── energy/
│       └── energy_forecast.pkl
│
├── notebooks/
│   ├── 01_exploration.ipynb         # EDA, visualisation
│   ├── 02_train_anomaly.ipynb       # anomaly detection training
│   ├── 03_train_fault_classifier.ipynb
│   ├── 04_train_rul_energy.ipynb
│   └── 05_experiments.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py                    # paths, thresholds, constants
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── stream_simulator.py      # reads from CSV, simulates 1s data
│   │
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── etl.py                   # clean, transform, save processed
│   │   └── features.py              # rolling windows, RMS, stats, etc.
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── anomaly_model.py         # load + infer anomaly model
│   │   ├── fault_model.py           # load + infer fault classifier
│   │   ├── rul_model.py             # load + infer RUL regressor
│   │   └── energy_model.py          # load + infer energy forecast
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── realtime_loop.py         # main real-time orchestrator
│   │
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── app.py                   # Streamlit/FastAPI frontend
│   │
│   └── storage/
│       ├── __init__.py
│       └── buffer.py                # in-memory / simple DB writer
│
├── scripts/
│   ├── train_anomaly.py
│   ├── train_fault.py
│   ├── train_rul.py
│   └── run_realtime_demo.py         # `python scripts/run_realtime_demo.py`
│
├── tests/
│   ├── test_features.py
│   ├── test_models.py
│   └── test_pipeline.py
│
├── requirements.txt
├── README.md
└── .gitignore








data/  -> raw dataset and cleaned/processed versions

models/  -> saved trained models (pickle, .pt, .onnx, etc.)

notebooks/ -> interactive exploration + model training experiments

src/ingestion/  -> everything that brings data in (simulation now, IoT later)

src/preprocessing/ -> ETL and feature engineering centralised

src/models/  -> thin wrappers that: load model, expose predict() / score() methods

src/pipeline/realtime_loop.py -> main AMOS brain: calls ingestion, calls preprocessing, calls models. sends results to storage + dashboard

src/dashboard/ -> Streamlit / FastAPI app to visualise current state

scripts/ -> CLI entrypoints: train models, run demo, etc.



                          ┌───────────────────────┐
                          │       app.py          │
                          │  Dashboard / API      │
                          │  (Streamlit / FastAPI)│
                          └───────────▲───────────┘
                                      │
                             pushes updates (HTTP/WS)
                                      │
                  ┌───────────────────┴──────────────────┐
                  │            realtime_loop.py          │
                  │     (MAIN orchestrator — 1s loop)    |
                  └───────────┬───────────┬──────────────┘
                              │           │
                        ingest data   run ML models
                              │           │
             ┌────────────────┘           └───────────────┐
             │                                             │
   stream_simulator.py                           models/, preprocessing/
 (fake MQTT/OPC/Kafka source)                    (feature builder, anomaly, fault)
