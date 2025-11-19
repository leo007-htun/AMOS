# AMOS - Predictive Maintenance System Usage Guide

## 🎯 What is AMOS?

AMOS (Anomaly detection, Maintenance Optimization System) is a **multi-model predictive maintenance system** that:

1. **Detects anomalies** in machine sensor data (IsolationForest)
2. **Predicts machine failures** with probability scores (RandomForest Binary Classifier)
3. **Identifies failure types** - TWF, HDF, PWF, OSF, RNF, or NORMAL (RandomForest Multiclass Classifier)
4. **Estimates Remaining Useful Life (RUL)** in minutes (RandomForest Regressor)
5. **Forecasts energy consumption** (RandomForest Regressor)
6. **Optimizes maintenance decisions** - when to schedule maintenance, expected costs, and action priorities

## 📊 System Architecture

```
Streaming Data → Anomaly Detection → Fault Classification → RUL Prediction → Optimization → Dashboard
                      ↓                    ↓                     ↓              ↓
                 Anomaly Score       Failure Type           RUL (min)    Maintenance Action
                                    (TWF/HDF/PWF/
                                     OSF/RNF/NORMAL)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare Data

The data is already processed, but you can regenerate it:

```bash
python3 -c "from src.preprocessing.etl import create_processed_dataset; create_processed_dataset(force=True)"
```

### 3. Train Models (Optional - already trained)

All models are already trained, but you can retrain them:

```bash
# Train anomaly detection model
python3 scripts/train_anomaly.py

# Train binary fault classifier
python3 scripts/train_fault.py

# Train multiclass fault classifier (identifies failure type)
PYTHONPATH=. python3 scripts/train_fault_multiclass.py

# Train RUL and energy models
python3 scripts/train_rul.py
```

### 4. Test the System

```bash
python3 scripts/test_pipeline.py
```

Expected output: All tests should pass ✓

### 5. Run the Dashboard

```bash
streamlit run src/dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

**Dashboard Features:**
- 🚨 **Critical Alerts** - Immediate action items at the top
- 📊 **Real-time Metrics** - Anomalies, failures, RUL, costs
- 📋 **Predictions Tab** - Latest predictions with failure types
- 📈 **Analytics Tab** - Time series charts and failure distribution
- 🔧 **Maintenance Queue** - Prioritized maintenance actions
- ⚡ **Real-time Monitor** - Live streaming data view

### 6. Run Console Demo (Alternative)

```bash
python3 scripts/run_realtime_demo.py
```

This will stream data and print predictions to console.

## 📂 Project Structure

```
AMOS/
├── data/
│   ├── raw/ai4i2020.csv                    # Original dataset
│   └── processed/ai4i2020_prepared.csv     # Processed data
│
├── models/
│   ├── anomaly/isolation_forest.pkl        # Anomaly detection
│   ├── fault/failure_classifier.pkl        # Binary fault classifier
│   ├── fault/fault_multiclass.pkl          # Multiclass fault classifier (NEW!)
│   ├── rul/rul_regressor.pkl               # RUL prediction
│   └── energy/energy_forecast.pkl          # Energy forecasting
│
├── src/
│   ├── config.py                           # Configuration and paths
│   ├── preprocessing/
│   │   ├── etl.py                          # Data processing
│   │   └── features.py                     # Feature engineering
│   ├── models/
│   │   ├── anomaly_model.py                # Anomaly detection
│   │   ├── fault_model.py                  # Binary fault classifier
│   │   ├── fault_multiclass_model.py       # Multiclass fault classifier (NEW!)
│   │   ├── rul_model.py                    # RUL prediction
│   │   ├── energy_model.py                 # Energy forecasting
│   │   └── optimization_model.py           # Maintenance optimization (NEW!)
│   ├── pipeline/
│   │   └── realtime_loop.py                # Main processing pipeline
│   ├── ingestion/
│   │   └── stream_simulator.py             # Data streaming simulator
│   ├── storage/
│   │   └── buffer.py                       # In-memory buffer
│   └── dashboard/
│       └── app.py                          # Streamlit dashboard
│
└── scripts/
    ├── train_*.py                          # Training scripts
    ├── test_pipeline.py                    # Test suite (NEW!)
    └── run_realtime_demo.py                # Console demo
```

## 🔧 Understanding the Models

### 1. Anomaly Detection Model
- **Algorithm:** IsolationForest
- **Purpose:** Detect unusual patterns that may indicate problems
- **Output:** Anomaly score (0-1, higher = more anomalous)
- **Threshold:** 0.6 (configurable in `config.py`)

### 2. Binary Fault Classifier
- **Algorithm:** RandomForest with SMOTE
- **Purpose:** Predict if machine will fail (yes/no)
- **Output:** Failure probability (0-1)
- **Threshold:** 0.35 (configurable in `config.py`)

### 3. Multiclass Fault Classifier (NEW!)
- **Algorithm:** RandomForest with SMOTE
- **Purpose:** Identify specific failure type
- **Output:** One of 6 classes:
  - **NORMAL** - No failure
  - **TWF** - Tool Wear Failure
  - **HDF** - Heat Dissipation Failure
  - **PWF** - Power Failure
  - **OSF** - Overstrain Failure
  - **RNF** - Random Failure
- **Accuracy:** 98.3% on test set

### 4. RUL (Remaining Useful Life) Model
- **Algorithm:** RandomForest Regressor
- **Purpose:** Estimate how much time until maintenance needed
- **Output:** Minutes until failure
- **Note:** Currently uses tool wear as proxy (simplified)

### 5. Energy Forecasting Model
- **Algorithm:** RandomForest Regressor
- **Purpose:** Predict energy consumption
- **Output:** Energy estimate

### 6. Optimization Model (NEW!)
- **Type:** Rule-based decision system
- **Purpose:** Recommend optimal maintenance actions
- **Decision Factors:**
  - Failure probability
  - Failure type
  - Remaining useful life
  - Anomaly detection
  - Cost analysis

## 🎯 Maintenance Decision Logic

The optimization model recommends actions based on this decision tree:

| Condition | Action | Priority | Description |
|-----------|--------|----------|-------------|
| Anomaly but no failure | INVESTIGATE | 3 | Check sensor data |
| Failure prob > 70% OR RUL < 30 min | CRITICAL_IMMEDIATE | 1 | Stop and fix now |
| Failure prob > 50% AND RUL < 60 min | SCHEDULE_URGENT | 2 | Within 1 shift |
| Failure prob > 35% AND RUL < 120 min | SCHEDULE_SOON | 4 | Within 1-2 days |
| Failure prob > 35% but high RUL | MONITOR | 5 | Continue watching |
| RUL < 60 min but low failure prob | SCHEDULE_SOON | 4 | Preventive maintenance |
| All OK | NORMAL | 6 | Continue operations |

### Cost Model

- **Scheduled Maintenance:** $500 + downtime cost
- **Unplanned Failure:** $5,000 + downtime cost
- **Downtime Cost:** $1,000/hour
- **Investigation:** $100

Expected cost = P(failure) × Failure cost + (1 - P(failure)) × Maintenance cost

## 📊 Dataset Information

**Source:** AI4I 2020 Predictive Maintenance Dataset
**Size:** 10,000 samples
**Features:**
- Type (L/M/H - Low/Medium/High quality)
- Air temperature [K]
- Process temperature [K]
- Rotational speed [rpm]
- Torque [Nm]
- Tool wear [min]

**Failure Modes Distribution:**
- NORMAL: 96.7%
- HDF: 1.15%
- PWF: 0.91%
- OSF: 0.78%
- TWF: 0.46%

**Derived Features:**
- Temp_diff = Process temp - Air temp
- Power_proxy = Speed × Torque
- Tool_wear_norm = Normalized tool wear

## ⚙️ Configuration

Edit `src/config.py` to adjust:

```python
# Thresholds
FAILURE_PROBA_THRESHOLD = 0.35      # Failure probability threshold
ANOMALY_SCORE_THRESHOLD = 0.6       # Anomaly detection threshold

# Optimization parameters
MAINTENANCE_COST = 500.0            # Scheduled maintenance cost ($)
FAILURE_COST = 5000.0               # Unplanned failure cost ($)
DOWNTIME_COST_PER_HOUR = 1000.0     # Downtime cost per hour ($)
RUL_SAFETY_MARGIN = 20.0            # Safety margin for RUL (minutes)

# Streaming
STREAM_SLEEP_SECONDS = 0.5          # Delay between rows
BUFFER_MAXLEN = 500                 # Buffer size
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python3 scripts/test_pipeline.py
```

**Tests included:**
1. ✓ Data loading and preprocessing
2. ✓ All models can be loaded
3. ✓ Single row prediction
4. ✓ Batch processing
5. ✓ Optimization decision logic

## 🐛 Troubleshooting

### ModuleNotFoundError: No module named 'src'

**Solution:** Use PYTHONPATH:
```bash
PYTHONPATH=. python3 scripts/your_script.py
```

### Model file not found

**Solution:** Train the model first:
```bash
PYTHONPATH=. python3 scripts/train_fault_multiclass.py
```

### Streamlit not found

**Solution:** Install dependencies:
```bash
pip install streamlit streamlit_autorefresh
```

## 📈 Next Steps & Improvements

### Short-term:
1. ✅ Implement multiclass fault classification → **DONE!**
2. ✅ Add optimization/decision model → **DONE!**
3. ✅ Enhanced dashboard with failure types → **DONE!**

### Medium-term:
- Improve RUL model with survival analysis (Weibull, Cox regression)
- Add real sensor data ingestion (MQTT, OPC-UA)
- Implement maintenance scheduling calendar
- Add cost tracking and ROI analysis

### Long-term:
- Deep learning models (LSTM for time-series RUL)
- Multi-machine fleet monitoring
- Automated alert notifications (email, Slack)
- Integration with CMMS systems

## 📝 Citation

If using the AI4I 2020 dataset, please cite:
```
Stephan Matzka, 'Explainable Artificial Intelligence for Predictive Maintenance Applications',
Third International Conference on Artificial Intelligence for Industries (AI4I 2020), 2020.
```

## 🤝 Support

For issues or questions:
1. Check this guide
2. Review code comments
3. Run test suite: `python3 scripts/test_pipeline.py`
4. Check model training logs

---

**Built with:** Python, scikit-learn, pandas, Streamlit
**License:** MIT
**Version:** 2.0 (with multiclass classification and optimization)
