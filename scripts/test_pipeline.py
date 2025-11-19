# scripts/test_pipeline.py
"""
Test the complete AMOS pipeline end-to-end

This script tests all components:
1. Data loading and preprocessing
2. All model loading and inference
3. Optimization decision making
4. Complete pipeline processing
"""

import pandas as pd
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.etl import create_processed_dataset
from src.config import PROCESSED_DATA_PATH
from src.pipeline.realtime_loop import RealtimePipeline


def test_data_loading():
    """Test 1: Data loading and preprocessing"""
    print("\n" + "=" * 70)
    print("TEST 1: Data Loading and Preprocessing")
    print("=" * 70)

    path = create_processed_dataset(force=False)
    df = pd.read_csv(path)

    print(f"✓ Loaded processed data from: {path}")
    print(f"✓ Total rows: {len(df)}")
    print(f"✓ Total columns: {len(df.columns)}")

    # Check FailureMode column
    print("\nFailure Mode Distribution:")
    failure_dist = df["FailureMode"].value_counts()
    print(failure_dist)

    # Verify no None values
    none_count = df["FailureMode"].isna().sum()
    if none_count == 0:
        print("✓ No None/NaN values in FailureMode column")
    else:
        print(f"✗ WARNING: {none_count} None/NaN values found in FailureMode")

    return df


def test_model_loading():
    """Test 2: All models can be loaded"""
    print("\n" + "=" * 70)
    print("TEST 2: Model Loading")
    print("=" * 70)

    try:
        from src.models.anomaly_model import load_anomaly_model
        from src.models.fault_model import load_fault_model
        from src.models.fault_multiclass_model import load_multiclass_fault_model
        from src.models.rul_model import load_rul_model
        from src.models.energy_model import load_energy_model

        print("Loading anomaly model...")
        anomaly_model = load_anomaly_model()
        print("✓ Anomaly model loaded")

        print("Loading binary fault model...")
        fault_binary_model = load_fault_model()
        print("✓ Binary fault model loaded")

        print("Loading multiclass fault model...")
        fault_multiclass_model = load_multiclass_fault_model()
        print("✓ Multiclass fault model loaded")

        print("Loading RUL model...")
        rul_model = load_rul_model()
        print("✓ RUL model loaded")

        print("Loading energy model...")
        energy_model = load_energy_model()
        print("✓ Energy model loaded")

        return True

    except Exception as e:
        print(f"✗ ERROR loading models: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_prediction(df):
    """Test 3: Single row prediction through all models"""
    print("\n" + "=" * 70)
    print("TEST 3: Single Row Prediction")
    print("=" * 70)

    try:
        pipeline = RealtimePipeline()
        print("✓ Pipeline initialized")

        # Get a sample row (preferably one with failure)
        sample_row = df.iloc[100]

        print(f"\nProcessing row 100...")
        print(f"  Type: {sample_row.get('Type', 'N/A')}")
        print(f"  Tool wear: {sample_row.get('Tool wear [min]', 'N/A')} min")
        print(f"  Actual Failure Mode: {sample_row.get('FailureMode', 'N/A')}")

        result = pipeline.process_row(sample_row, 100)

        print("\n📊 Prediction Results:")
        print(f"  Anomaly Score: {result.anomaly_score:.3f} (flag={result.anomaly_flag})")
        print(f"  Failure Probability: {result.failure_proba:.3f} (flag={result.failure_flag})")
        print(f"  Predicted Failure Mode: {result.failure_mode} (confidence={result.failure_mode_confidence:.3f})")
        print(f"  RUL Estimate: {result.rul_estimate:.1f} minutes")
        print(f"  Energy Estimate: {result.energy_estimate:.2f}")

        print("\n🔧 Maintenance Decision:")
        print(f"  Action: {result.maintenance_action.upper()}")
        print(f"  Priority: {result.maintenance_priority}")
        print(f"  Expected Cost: ${result.expected_cost:.2f}")
        print(f"  Reasoning: {result.maintenance_reasoning}")
        if result.scheduled_time:
            print(f"  Scheduled Time: {result.scheduled_time}")

        print("\n✓ Single prediction successful!")
        return True

    except Exception as e:
        print(f"✗ ERROR in single prediction: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_processing(df):
    """Test 4: Batch processing"""
    print("\n" + "=" * 70)
    print("TEST 4: Batch Processing (20 rows)")
    print("=" * 70)

    try:
        pipeline = RealtimePipeline()

        # Process 20 rows
        num_rows = 20
        results = []

        print(f"Processing {num_rows} rows...")
        for i in range(num_rows):
            row = df.iloc[i]
            result = pipeline.process_row(row, i)
            results.append(result)

            # Print summary every 5 rows
            if (i + 1) % 5 == 0:
                print(f"  Processed {i + 1}/{num_rows} rows...")

        print(f"✓ Successfully processed {len(results)} rows")

        # Analyze results
        print("\n📈 Batch Statistics:")
        anomaly_count = sum(1 for r in results if r.anomaly_flag)
        failure_count = sum(1 for r in results if r.failure_flag)
        critical_count = sum(1 for r in results if r.maintenance_priority <= 2)

        print(f"  Anomalies detected: {anomaly_count}/{num_rows}")
        print(f"  Failure alerts: {failure_count}/{num_rows}")
        print(f"  Critical actions needed: {critical_count}/{num_rows}")

        # Failure mode distribution
        failure_modes = {}
        for r in results:
            failure_modes[r.failure_mode] = failure_modes.get(r.failure_mode, 0) + 1

        print("\n  Predicted Failure Modes:")
        for mode, count in sorted(failure_modes.items(), key=lambda x: -x[1]):
            print(f"    {mode}: {count}")

        # Action distribution
        actions = {}
        for r in results:
            actions[r.maintenance_action] = actions.get(r.maintenance_action, 0) + 1

        print("\n  Maintenance Actions:")
        for action, count in sorted(actions.items(), key=lambda x: -x[1]):
            print(f"    {action}: {count}")

        print("\n✓ Batch processing successful!")
        return True

    except Exception as e:
        print(f"✗ ERROR in batch processing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_optimization_logic():
    """Test 5: Optimization decision logic"""
    print("\n" + "=" * 70)
    print("TEST 5: Optimization Decision Logic")
    print("=" * 70)

    try:
        from src.models.optimization_model import optimize_maintenance_decision
        from datetime import datetime

        test_cases = [
            {
                "name": "Critical - High failure prob",
                "failure_probability": 0.85,
                "failure_mode": "TWF",
                "rul_estimate": 100.0,
                "anomaly_score": 0.5,
                "anomaly_flag": False,
            },
            {
                "name": "Critical - Low RUL",
                "failure_probability": 0.3,
                "failure_mode": "HDF",
                "rul_estimate": 20.0,
                "anomaly_score": 0.4,
                "anomaly_flag": False,
            },
            {
                "name": "Normal operation",
                "failure_probability": 0.1,
                "failure_mode": "NORMAL",
                "rul_estimate": 200.0,
                "anomaly_score": 0.3,
                "anomaly_flag": False,
            },
            {
                "name": "Anomaly detected",
                "failure_probability": 0.2,
                "failure_mode": "NORMAL",
                "rul_estimate": 150.0,
                "anomaly_score": 0.8,
                "anomaly_flag": True,
            },
        ]

        for i, test in enumerate(test_cases, 1):
            print(f"\n  Test Case {i}: {test['name']}")
            decision = optimize_maintenance_decision(
                failure_probability=test["failure_probability"],
                failure_mode=test["failure_mode"],
                rul_estimate=test["rul_estimate"],
                anomaly_score=test["anomaly_score"],
                anomaly_flag=test["anomaly_flag"],
                current_time=datetime.now(),
            )

            print(f"    → Action: {decision.action.value}")
            print(f"    → Priority: {decision.confidence:.2f}")
            print(f"    → Cost: ${decision.expected_cost:.2f}")

        print("\n✓ Optimization logic tests passed!")
        return True

    except Exception as e:
        print(f"✗ ERROR in optimization tests: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 AMOS PIPELINE COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    results = {}

    # Run tests
    df = test_data_loading()
    results["Data Loading"] = df is not None and len(df) > 0

    results["Model Loading"] = test_model_loading()

    if results["Model Loading"]:
        results["Single Prediction"] = test_single_prediction(df)
        results["Batch Processing"] = test_batch_processing(df)

    results["Optimization Logic"] = test_optimization_logic()

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("\nYour AMOS system is ready to use!")
        print("\nNext steps:")
        print("  1. Run the dashboard: streamlit run src/dashboard/app.py")
        print("  2. Or run console demo: python scripts/run_realtime_demo.py")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print("=" * 70)
        print("\nPlease review the errors above and fix before deploying.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
