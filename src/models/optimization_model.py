# src/models/optimization_model.py
"""
Maintenance Optimization Model

This module implements decision logic for predictive maintenance scheduling
based on multi-model predictions from anomaly detection, fault classification,
and RUL estimation.

Key Decision Rules:
1. CRITICAL: High failure probability + Low RUL → Schedule immediately
2. WARNING: Moderate failure probability + Moderate RUL → Schedule within safety margin
3. MONITOR: Low failure probability + High RUL → Continue monitoring
4. ANOMALY: Anomaly detected → Investigate
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum

from src.config import (
    FAILURE_PROBA_THRESHOLD,
    ANOMALY_SCORE_THRESHOLD,
    MAINTENANCE_COST,
    FAILURE_COST,
    DOWNTIME_COST_PER_HOUR,
    RUL_SAFETY_MARGIN,
)


class MaintenanceAction(Enum):
    """Recommended maintenance actions"""
    CRITICAL_IMMEDIATE = "critical_immediate"  # Stop and fix now
    SCHEDULE_URGENT = "schedule_urgent"  # Schedule within 1 shift
    SCHEDULE_SOON = "schedule_soon"  # Schedule within 1-2 days
    MONITOR = "monitor"  # Continue monitoring
    INVESTIGATE = "investigate"  # Anomaly detected, needs investigation
    NORMAL = "normal"  # Operating normally


@dataclass
class MaintenanceDecision:
    """
    Maintenance decision output with recommendation and cost analysis
    """
    action: MaintenanceAction
    confidence: float  # 0-1, confidence in the decision
    failure_mode: str  # Type of failure: NORMAL, TWF, HDF, PWF, OSF, RNF
    failure_probability: float
    rul_estimate: float  # minutes
    anomaly_score: float
    expected_cost: float  # Expected cost if following this recommendation
    scheduled_time: Optional[datetime]  # When to schedule maintenance
    reasoning: str  # Human-readable explanation


def compute_expected_cost(
    failure_proba: float,
    rul_estimate: float,
    action: MaintenanceAction,
) -> float:
    """
    Compute expected cost based on decision

    Expected Cost = P(failure) × Failure Cost + (1 - P(failure)) × Maintenance Cost

    Args:
        failure_proba: Probability of failure (0-1)
        rul_estimate: Remaining useful life in minutes
        action: Recommended action

    Returns:
        Expected cost in dollars
    """
    if action == MaintenanceAction.CRITICAL_IMMEDIATE:
        # Immediate maintenance: higher downtime cost but prevent catastrophic failure
        downtime_hours = 2.0  # Assume 2 hours for emergency maintenance
        return MAINTENANCE_COST + (downtime_hours * DOWNTIME_COST_PER_HOUR)

    elif action == MaintenanceAction.SCHEDULE_URGENT:
        # Scheduled urgent maintenance: planned downtime
        downtime_hours = 1.5
        return MAINTENANCE_COST + (downtime_hours * DOWNTIME_COST_PER_HOUR)

    elif action == MaintenanceAction.SCHEDULE_SOON:
        # Scheduled maintenance: minimal downtime
        downtime_hours = 1.0
        return MAINTENANCE_COST + (downtime_hours * DOWNTIME_COST_PER_HOUR)

    elif action in [MaintenanceAction.MONITOR, MaintenanceAction.NORMAL]:
        # No immediate action: risk of failure
        # Expected cost = P(fail) × failure cost + P(not fail) × 0
        return failure_proba * FAILURE_COST

    elif action == MaintenanceAction.INVESTIGATE:
        # Investigation cost (minimal)
        return 100.0

    return 0.0


def optimize_maintenance_decision(
    failure_probability: float,
    failure_mode: str,
    rul_estimate: float,
    anomaly_score: float,
    anomaly_flag: bool,
    current_time: Optional[datetime] = None,
) -> MaintenanceDecision:
    """
    Make optimal maintenance decision based on multi-model predictions

    Decision Logic:
    1. If anomaly detected → INVESTIGATE
    2. If failure_proba > 0.7 OR RUL < 30 min → CRITICAL_IMMEDIATE
    3. If failure_proba > 0.5 AND RUL < 60 min → SCHEDULE_URGENT
    4. If failure_proba > THRESHOLD AND RUL < 120 min → SCHEDULE_SOON
    5. Otherwise → MONITOR or NORMAL

    Args:
        failure_probability: Probability of machine failure (0-1)
        failure_mode: Predicted failure type (NORMAL, TWF, HDF, PWF, OSF, RNF)
        rul_estimate: Remaining useful life estimate (minutes)
        anomaly_score: Anomaly detection score
        anomaly_flag: Whether anomaly threshold exceeded
        current_time: Current timestamp (defaults to now)

    Returns:
        MaintenanceDecision with action, reasoning, and cost analysis
    """
    if current_time is None:
        current_time = datetime.now()

    # Decision tree logic
    action: MaintenanceAction
    scheduled_time: Optional[datetime] = None
    reasoning: str
    confidence: float

    # Rule 1: Anomaly detected (high priority for investigation)
    if anomaly_flag and failure_mode == "NORMAL":
        action = MaintenanceAction.INVESTIGATE
        confidence = min(anomaly_score, 0.95)
        reasoning = (
            f"Anomaly detected (score={anomaly_score:.2f}) without failure prediction. "
            "Investigate sensor data and machine behavior."
        )
        scheduled_time = current_time + timedelta(hours=2)

    # Rule 2: Critical - immediate action required
    elif failure_probability > 0.7 or rul_estimate < 30:
        action = MaintenanceAction.CRITICAL_IMMEDIATE
        confidence = max(failure_probability, 1.0 - (rul_estimate / 30.0))
        reasoning = (
            f"CRITICAL: High failure risk (P={failure_probability:.2%}) "
            f"or very low RUL ({rul_estimate:.0f} min). "
            f"Predicted failure mode: {failure_mode}. Stop machine and perform maintenance NOW."
        )
        scheduled_time = current_time

    # Rule 3: Urgent - schedule within current shift
    elif failure_probability > 0.5 and rul_estimate < 60:
        action = MaintenanceAction.SCHEDULE_URGENT
        confidence = failure_probability * 0.9
        reasoning = (
            f"URGENT: Elevated failure risk (P={failure_probability:.2%}) "
            f"with low RUL ({rul_estimate:.0f} min). "
            f"Predicted failure mode: {failure_mode}. Schedule maintenance within this shift."
        )
        # Schedule within 4 hours or when RUL - safety margin
        schedule_delay_minutes = max(min(rul_estimate - RUL_SAFETY_MARGIN, 240), 30)
        scheduled_time = current_time + timedelta(minutes=schedule_delay_minutes)

    # Rule 4: Schedule soon - plan within 1-2 days
    elif failure_probability > FAILURE_PROBA_THRESHOLD and rul_estimate < 120:
        action = MaintenanceAction.SCHEDULE_SOON
        confidence = failure_probability * 0.8
        reasoning = (
            f"WARNING: Moderate failure risk (P={failure_probability:.2%}) "
            f"with RUL={rul_estimate:.0f} min. "
            f"Predicted failure mode: {failure_mode}. Plan maintenance within 1-2 days."
        )
        schedule_delay_minutes = max(rul_estimate - RUL_SAFETY_MARGIN, 60)
        scheduled_time = current_time + timedelta(minutes=schedule_delay_minutes)

    # Rule 5: High failure probability but good RUL
    elif failure_probability > FAILURE_PROBA_THRESHOLD:
        action = MaintenanceAction.MONITOR
        confidence = 0.7
        reasoning = (
            f"MONITOR: Moderate failure risk (P={failure_probability:.2%}) "
            f"but adequate RUL ({rul_estimate:.0f} min). "
            f"Continue monitoring. Potential failure mode: {failure_mode}."
        )
        scheduled_time = None

    # Rule 6: Low RUL but low failure probability
    elif rul_estimate < 60:
        action = MaintenanceAction.SCHEDULE_SOON
        confidence = 0.6
        reasoning = (
            f"Low RUL ({rul_estimate:.0f} min) approaching end of life. "
            f"Schedule preventive maintenance even though failure probability is low "
            f"(P={failure_probability:.2%})."
        )
        schedule_delay_minutes = max(rul_estimate - RUL_SAFETY_MARGIN, 30)
        scheduled_time = current_time + timedelta(minutes=schedule_delay_minutes)

    # Rule 7: Normal operation
    else:
        action = MaintenanceAction.NORMAL
        confidence = 1.0 - failure_probability
        reasoning = (
            f"Normal operation. Low failure risk (P={failure_probability:.2%}), "
            f"RUL={rul_estimate:.0f} min. Continue normal monitoring."
        )
        scheduled_time = None

    # Compute expected cost
    expected_cost = compute_expected_cost(failure_probability, rul_estimate, action)

    return MaintenanceDecision(
        action=action,
        confidence=min(confidence, 1.0),
        failure_mode=failure_mode,
        failure_probability=failure_probability,
        rul_estimate=rul_estimate,
        anomaly_score=anomaly_score,
        expected_cost=expected_cost,
        scheduled_time=scheduled_time,
        reasoning=reasoning,
    )


def get_maintenance_priority(decision: MaintenanceDecision) -> int:
    """
    Get numeric priority for sorting (1 = highest priority)

    Returns:
        Priority level: 1-6 (1 is most urgent)
    """
    priority_map = {
        MaintenanceAction.CRITICAL_IMMEDIATE: 1,
        MaintenanceAction.SCHEDULE_URGENT: 2,
        MaintenanceAction.INVESTIGATE: 3,
        MaintenanceAction.SCHEDULE_SOON: 4,
        MaintenanceAction.MONITOR: 5,
        MaintenanceAction.NORMAL: 6,
    }
    return priority_map.get(decision.action, 6)


def format_decision_summary(decision: MaintenanceDecision) -> str:
    """
    Format decision as human-readable summary

    Returns:
        Formatted string for display
    """
    action_emoji = {
        MaintenanceAction.CRITICAL_IMMEDIATE: "🚨",
        MaintenanceAction.SCHEDULE_URGENT: "⚠️",
        MaintenanceAction.SCHEDULE_SOON: "⚡",
        MaintenanceAction.INVESTIGATE: "🔍",
        MaintenanceAction.MONITOR: "👁️",
        MaintenanceAction.NORMAL: "✅",
    }

    emoji = action_emoji.get(decision.action, "")
    action_name = decision.action.value.upper().replace("_", " ")

    summary = f"{emoji} {action_name}\n"
    summary += f"Failure Mode: {decision.failure_mode}\n"
    summary += f"Failure Probability: {decision.failure_probability:.1%}\n"
    summary += f"RUL: {decision.rul_estimate:.0f} min\n"
    summary += f"Confidence: {decision.confidence:.1%}\n"
    summary += f"Expected Cost: ${decision.expected_cost:.2f}\n"

    if decision.scheduled_time:
        summary += f"Schedule: {decision.scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"

    summary += f"\nReasoning: {decision.reasoning}"

    return summary
