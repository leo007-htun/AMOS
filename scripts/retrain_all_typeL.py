#!/usr/bin/env python3
"""
Retrain all models on Type L data only for optimal single-product performance.
"""
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PROCESSED_DATA_PATH
from src.models.anomaly_model import train_anomaly_model, save_anomaly_model
from src.models.fault_model import train_fault_classifier, save_fault_model
from src.models.fault_multiclass_model import train_multiclass_fault_classifier, save_multiclass_fault_model
from src.models.rul_model import train_rul_model, save_rul_model
from src.models.energy_model import train_energy_model, save_energy_model


def main():
    print("=" * 70)
    print("RETRAINING ALL MODELS ON TYPE L DATA ONLY")
    print("=" * 70)

    # Load full processed data
    print(f"\n📂 Loading data from: {PROCESSED_DATA_PATH}")
    df = pd.read_csv(PROCESSED_DATA_PATH)
    print(f"  Total samples: {len(df)}")

    # Filter to Type L only
    df_L = df[df["Type"] == "L"].copy()
    print(f"\n🔍 Filtered to Type L only: {len(df_L)} samples")

    # 1. Train Anomaly Detection
    print("\n" + "=" * 70)
    print("1️⃣  TRAINING ANOMALY DETECTION MODEL")
    print("=" * 70)
    try:
        anomaly_model = train_anomaly_model(df_L)
        save_anomaly_model(anomaly_model)
        print("✅ Anomaly model trained and saved")
    except Exception as e:
        print(f"❌ Error training anomaly model: {e}")

    # 2. Train Binary Fault Classifier
    print("\n" + "=" * 70)
    print("2️⃣  TRAINING BINARY FAULT CLASSIFIER")
    print("=" * 70)
    try:
        fault_model, metrics = train_fault_classifier(df_L)
        save_fault_model(fault_model)
        print("✅ Binary fault model trained and saved")
        print(f"   ROC-AUC: {metrics.get('roc_auc', 'N/A')}")
    except Exception as e:
        print(f"❌ Error training binary fault model: {e}")

    # 3. Train Multiclass Fault Classifier
    print("\n" + "=" * 70)
    print("3️⃣  TRAINING MULTICLASS FAULT CLASSIFIER")
    print("=" * 70)
    try:
        multiclass_model, metrics = train_multiclass_fault_classifier(df_L)
        save_multiclass_fault_model(multiclass_model)
        print("✅ Multiclass fault model trained and saved")

        # Print class-wise metrics
        if "classification_report" in metrics:
            report = metrics["classification_report"]
            print("\n   Class-wise Performance:")
            for class_name, class_metrics in report.items():
                if isinstance(class_metrics, dict) and 'precision' in class_metrics:
                    print(f"     {class_name:10s}: Precision={class_metrics['precision']:.3f}, "
                          f"Recall={class_metrics['recall']:.3f}, "
                          f"F1={class_metrics['f1-score']:.3f}")
    except Exception as e:
        print(f"❌ Error training multiclass fault model: {e}")

    # 4. Train RUL Model
    print("\n" + "=" * 70)
    print("4️⃣  TRAINING RUL MODEL")
    print("=" * 70)
    try:
        rul_model, metrics = train_rul_model(df_L)
        save_rul_model(rul_model)
        print("✅ RUL model trained and saved")
        print(f"   R²: {metrics.get('r2', 'N/A')}")
        print(f"   MAE: {metrics.get('mae', 'N/A'):.2f}")
    except Exception as e:
        print(f"❌ Error training RUL model: {e}")

    # 5. Train Energy Model
    print("\n" + "=" * 70)
    print("5️⃣  TRAINING ENERGY MODEL")
    print("=" * 70)
    try:
        energy_model, metrics = train_energy_model(df_L)
        save_energy_model(energy_model)
        print("✅ Energy model trained and saved")
        print(f"   R²: {metrics.get('r2', 'N/A')}")
        print(f"   MAE: {metrics.get('mae', 'N/A'):.2f}")
    except Exception as e:
        print(f"❌ Error training energy model: {e}")

    print("\n" + "=" * 70)
    print("🎉 MODEL RETRAINING COMPLETE!")
    print("=" * 70)
    print("\n✅ All models retrained on Type L data only")
    print("✅ Models optimized for single-product production line")
    print("\n🚀 Ready to launch: streamlit run src/dashboard/app.py")


if __name__ == "__main__":
    main()
