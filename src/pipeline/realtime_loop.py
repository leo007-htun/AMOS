# src/pipeline/realtime_loop.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd

from src.config import (
    FAILURE_PROBA_THRESHOLD,
    ANOMALY_SCORE_THRESHOLD,
    BUFFER_MAXLEN,
)
from src.ingestion.stream_simulator import StreamSimulator
from src.models.anomaly_model import load_anomaly_model, compute_anomaly_score
from src.models.energy_model import load_energy_model, predict_energy
from src.models.fault_model import load_fault_model, failure_probability
from src.models.fault_multiclass_model import (
    load_multiclass_fault_model,
    predict_failure_mode,
    predict_failure_mode_proba,
)
from src.models.rul_model import load_rul_model, predict_rul
from src.models.optimization_model import (
    optimize_maintenance_decision,
    get_maintenance_priority,
    MaintenanceDecision,
)
from src.preprocessing.features import build_single_row_feature_df
from src.storage.buffer import InMemoryBuffer


@dataclass
class RealtimeOutput:
    row_index: int
    raw_row: Dict[str, Any]
    anomaly_score: float
    anomaly_flag: bool
    failure_proba: float
    failure_flag: bool
    failure_mode: str  # Predicted failure type: NORMAL, TWF, HDF, PWF, OSF, RNF
    failure_mode_confidence: float  # Confidence of failure mode prediction
    rul_estimate: float
    energy_estimate: float
    maintenance_action: str  # Recommended action from optimization
    maintenance_priority: int  # Priority level (1=highest)
    maintenance_reasoning: str  # Explanation of decision
    expected_cost: float  # Expected cost
    scheduled_time: Optional[str]  # Scheduled maintenance time (ISO format)


class RealtimePipeline:
    """
    Orchestrates ingestion, preprocessing, model inference, optimization, and buffering.

    Models:
    - Anomaly detection (IsolationForest)
    - Binary fault classification (RandomForest)
    - Multiclass fault classification (RandomForest) - identifies failure type
    - RUL prediction (RandomForest Regressor)
    - Energy forecasting (RandomForest Regressor)
    - Maintenance optimization (rule-based decision system)
    """

    def __init__(self):
        print("Loading models...")
        self.anomaly_model = load_anomaly_model()
        self.fault_binary_model = load_fault_model()
        self.fault_multiclass_model = load_multiclass_fault_model()
        self.rul_model = load_rul_model()
        self.energy_model = load_energy_model()
        self.buffer = InMemoryBuffer(maxlen=BUFFER_MAXLEN)
        print("All models loaded successfully!")

    def process_row(self, row: pd.Series, idx: int) -> RealtimeOutput:
        """
        Process a single row through all models and optimization

        Steps:
        1. Anomaly detection
        2. Binary fault prediction (probability)
        3. Multiclass fault prediction (failure type)
        4. RUL estimation
        5. Energy forecasting
        6. Maintenance optimization decision
        """
        X = build_single_row_feature_df(row)

        # 1. Anomaly detection
        a_scores = compute_anomaly_score(self.anomaly_model, X)
        anomaly_score = float(a_scores[0])
        anomaly_flag = anomaly_score >= ANOMALY_SCORE_THRESHOLD

        # 2. Binary fault prediction
        f_proba = failure_probability(self.fault_binary_model, X)
        failure_proba = float(f_proba[0])
        failure_flag = failure_proba >= FAILURE_PROBA_THRESHOLD

        # 3. Multiclass fault prediction (failure type)
        failure_mode_pred = predict_failure_mode(self.fault_multiclass_model, X)
        failure_mode = str(failure_mode_pred[0])

        # Get confidence for the predicted failure mode
        failure_mode_proba = predict_failure_mode_proba(self.fault_multiclass_model, X)
        failure_mode_confidence = float(failure_mode_proba[0].max())

        # 4. RUL estimation
        rul_pred = predict_rul(self.rul_model, X)
        rul_estimate = float(rul_pred[0])

        # 5. Energy forecasting
        energy_pred = predict_energy(self.energy_model, X)
        energy_estimate = float(energy_pred[0])

        # 6. Maintenance optimization decision
        decision: MaintenanceDecision = optimize_maintenance_decision(
            failure_probability=failure_proba,
            failure_mode=failure_mode,
            rul_estimate=rul_estimate,
            anomaly_score=anomaly_score,
            anomaly_flag=anomaly_flag,
            current_time=datetime.now(),
        )

        # Format scheduled time as ISO string if exists
        scheduled_time_str = None
        if decision.scheduled_time:
            scheduled_time_str = decision.scheduled_time.isoformat()

        out = RealtimeOutput(
            row_index=idx,
            raw_row=row.to_dict(),
            anomaly_score=anomaly_score,
            anomaly_flag=anomaly_flag,
            failure_proba=failure_proba,
            failure_flag=failure_flag,
            failure_mode=failure_mode,
            failure_mode_confidence=failure_mode_confidence,
            rul_estimate=rul_estimate,
            energy_estimate=energy_estimate,
            maintenance_action=decision.action.value,
            maintenance_priority=get_maintenance_priority(decision),
            maintenance_reasoning=decision.reasoning,
            expected_cost=decision.expected_cost,
            scheduled_time=scheduled_time_str,
        )

        self.buffer.append(out.__dict__)
        return out

    def run_forever(self):
        stream = StreamSimulator(loop_forever=True)
        for idx, row in enumerate(stream):
            out = self.process_row(row, idx)

            # Enhanced console logging with failure mode and maintenance decision
            action_emoji = {
                "critical_immediate": "🚨",
                "schedule_urgent": "⚠️",
                "schedule_soon": "⚡",
                "investigate": "🔍",
                "monitor": "👁️",
                "normal": "✅",
            }
            emoji = action_emoji.get(out.maintenance_action, "")

            print(
                f"[Row {out.row_index}] {emoji} "
                f"Mode={out.failure_mode} | "
                f"FailProba={out.failure_proba:.3f} | "
                f"RUL={out.rul_estimate:.0f}min | "
                f"Action={out.maintenance_action.upper()} | "
                f"Cost=${out.expected_cost:.0f}"
            )
