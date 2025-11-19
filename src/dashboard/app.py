# src/dashboard/app.py

import os
import sys
import time
from pathlib import Path

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Make project root importable automatically (AMOS/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Hardcode the stream CSV path relative to the project root.
# Adjust the filename here if needed to match what you actually have.
STREAM_PATH = PROJECT_ROOT / "data" / "processed" / "ai4i2020_stream_realistic.csv"
# or, if you're using the correlated one:
# STREAM_PATH = PROJECT_ROOT / "data" / "processed" / "ai4i2020_stream_realistic_correlated.csv"

from src.pipeline.realtime_loop import RealtimePipeline



def init_state():
    # Shared pipeline + buffer
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = RealtimePipeline()

    # Load full stream data once (realistic stream CSV - Type L only, sorted by wear)
    if "stream_df" not in st.session_state:
        #from src.config import REALISTIC_STREAM_PATH
        df = pd.read_csv(STREAM_PATH)
        st.session_state["stream_df"] = df

    # Current position in the stream dataframe
    if "stream_pos" not in st.session_state:
        st.session_state["stream_pos"] = 0

    # Auto-run flag
    if "auto_run" not in st.session_state:
        st.session_state["auto_run"] = False

    # Last processed timestamp (optional)
    if "last_processed" not in st.session_state:
        st.session_state["last_processed"] = None

    # 🔒 Pause streaming when there are unresolved CRITICAL alerts
    if "stream_paused" not in st.session_state:
        st.session_state["stream_paused"] = False

    # ✅ Track which critical rows have been marked as fixed (store row_index values)
    if "resolved_critical_rows" not in st.session_state:
        st.session_state["resolved_critical_rows"] = []


def process_batch(pipeline: RealtimePipeline, batch_size: int) -> int:
    """
    Take the next batch_size rows from stream_df starting at stream_pos,
    push them through the pipeline, and advance stream_pos.
    Returns how many rows were processed.
    """
    df = st.session_state["stream_df"]
    pos = st.session_state["stream_pos"]

    if pos >= len(df):
        return 0  # end of stream

    end = min(pos + batch_size, len(df))
    rows = df.iloc[pos:end]

    # Use sequential streaming index (pos, pos+1, pos+2...) instead of DataFrame index
    for i, (_, row) in enumerate(rows.iterrows()):
        streaming_idx = pos + i
        pipeline.process_row(row, streaming_idx)

    st.session_state["stream_pos"] = end
    st.session_state["last_processed"] = time.time()

    return len(rows)


def get_action_color(action: str) -> str:
    """Return color based on maintenance action priority"""
    colors = {
        "critical_immediate": "red",
        "schedule_urgent": "orange",
        "schedule_soon": "yellow",
        "investigate": "blue",
        "monitor": "gray",
        "normal": "green",
    }
    return colors.get(action, "gray")


def main():
    st.set_page_config(page_title="AMOS Realtime Monitoring", layout="wide")
    st.title("🏭 AMOS - Predictive Maintenance System")
    st.caption("Anomaly detection • Fault classification • RUL prediction • Maintenance optimization")

    # Initialize all state first
    init_state()
    pipeline: RealtimePipeline = st.session_state["pipeline"]

    # Show data source info
    if "stream_df" in st.session_state:
        tool_wear_vals = st.session_state["stream_df"]["Tool wear [min]"].head(20).tolist()
        is_sorted = tool_wear_vals == sorted(tool_wear_vals)
        if is_sorted:
            st.success("📊 Using REALISTIC stream (sorted by tool wear - simulates gradual tool degradation)")
        else:
            st.warning("⚠️ Using SHUFFLED data (random order - not realistic for production monitoring)")

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Streaming Controls")

        batch_size = st.slider(
            "Rows per update",
            min_value=1,
            max_value=50,
            value=5,
            step=1,
            help="How many new rows to process on each auto-refresh",
        )

        refresh_ms = st.slider(
            "Refresh interval (ms)",
            min_value=200,
            max_value=5000,
            value=1000,
            step=100,
            help="How often the dashboard refreshes and processes a batch",
        )

        auto_run = st.checkbox(
            "Auto-run stream",
            value=st.session_state["auto_run"],
            help="Continuously process new rows and update the dashboard",
        )
        st.session_state["auto_run"] = auto_run

        if st.button("Process one batch now"):
            if st.session_state["stream_paused"]:
                st.warning("⏸️ Stream is paused due to unresolved CRITICAL alerts. Mark them as fixed first.")
            else:
                processed = process_batch(pipeline, batch_size)
                st.success(f"Manually processed {processed} rows.")

        st.write("---")
        st.write(f"📊 Total rows processed: {st.session_state['stream_pos']} / {len(st.session_state['stream_df'])}")

        if st.session_state["stream_paused"]:
            st.error("⏸️ Streaming paused: unresolved CRITICAL alerts.")
        else:
            st.success("▶️ Streaming enabled")

    # Auto-refresh: rerun script every refresh_ms
    _ = st_autorefresh(interval=refresh_ms, limit=None, key="amos_autorefresh")

    # If auto-run is enabled AND not paused, process a small batch on each rerun
    if st.session_state["auto_run"]:
        if st.session_state["stream_paused"]:
            st.warning("⏸️ Stream is paused due to unresolved CRITICAL alerts. Resolve them to resume.")
        else:
            processed = process_batch(pipeline, batch_size)
            if processed == 0:
                st.warning("End of stream reached. Disable auto-run or restart the app to reset.")

    # Show data from buffer
    latest = pipeline.buffer.latest(300)
    if not latest:
        st.info("No data processed yet. Use the sidebar to process a batch or enable auto-run.")
        return

    df_buf = pd.DataFrame(latest)

    # Apply cost reset per resolved critical rows (row_index in resolved_critical_rows → cost=0 for analytics)
    resolved_rows = set(st.session_state.get("resolved_critical_rows", []))

    # 🔒 If required columns are not present yet (e.g. early in stream), just default cost to 0
    required_cols = {"maintenance_action", "expected_cost", "row_index"}
    if not required_cols.issubset(df_buf.columns):
        df_buf["effective_expected_cost"] = 0.0
    else:
        def compute_effective_cost(row):
            # No cost for normal/monitor actions
            action = row.get("maintenance_action", None)
            if action in ["normal", "monitor"]:
                return 0.0

            # No cost for resolved critical rows
            if row.get("row_index") in resolved_rows:
                return 0.0

            # Fallback: if expected_cost is missing, treat as 0
            return float(row.get("expected_cost", 0.0))

        df_buf["effective_expected_cost"] = df_buf.apply(compute_effective_cost, axis=1)


    # === TOP SECTION: Critical Alerts ===
    # Critical = maintenance_priority <= 2

        # === TOP SECTION: Critical Alerts ===
    # If maintenance_priority isn't available yet (e.g. early warm-up), don't crash
    if "maintenance_priority" not in df_buf.columns:
        st.info("Model outputs not ready yet (no maintenance_priority in buffer). "
                "Process a few more rows or wait for the pipeline to warm up.")
        return

    # Critical = maintenance_priority <= 2
    critical_alerts = df_buf[df_buf["maintenance_priority"] <= 2].sort_values("maintenance_priority")


    # Only enforce pause for alerts that have NOT been marked fixed
    unresolved_critical = critical_alerts[~critical_alerts["row_index"].isin(resolved_rows)]

    # Set/clear pause flag based on unresolved critical alerts
    st.session_state["stream_paused"] = len(unresolved_critical) > 0

    if len(unresolved_critical) > 0:
        st.error(f"🚨 {len(unresolved_critical)} CRITICAL ALERTS requiring immediate attention!")
        st.warning("⏸️ Streaming is paused until all CRITICAL alerts are marked as fixed.")

        for _, alert in unresolved_critical.head(5).iterrows():
            # Create product/machine ID for alert
            alert_machine_type = alert["raw_row"].get("Type", "?")
            alert_machine_id = f"Product-{alert_machine_type}-{alert['row_index']:04d}"

            with st.expander(f"⚠️ {alert_machine_id} - {alert['maintenance_action'].upper()}", expanded=True):
                st.markdown(f"**Product ID:** {alert_machine_id}")
                st.markdown(f"**Failure Mode:** {alert['failure_mode']}")
                st.markdown(f"**Failure Probability:** {alert['failure_proba']:.1%}")
                st.markdown(f"**RUL:** {alert['rul_estimate']:.0f} minutes")
                st.markdown(f"**Expected Cost:** ${alert['expected_cost']:.2f}")
                st.info(alert["maintenance_reasoning"])

                # ✅ Button to mark this critical alert as fixed
                if st.button("✅ Mark as fixed", key=f"resolve_{alert['row_index']}"):
                    st.session_state["resolved_critical_rows"].append(alert["row_index"])
                    st.success("Marked as fixed. This alert will be cleared on next refresh.")
    else:
        # No unresolved critical -> stream can run freely
        st.session_state["stream_paused"] = False

    # === METRICS ROW ===
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

    with col_m1:
        anomaly_count = df_buf["anomaly_flag"].sum()
        st.metric("Anomalies Detected", anomaly_count)

    with col_m2:
        failure_count = df_buf["failure_flag"].sum()
        st.metric("Failure Alerts", failure_count)

    with col_m3:
        avg_rul = df_buf["rul_estimate"].mean()
        st.metric("Avg RUL", f"{avg_rul:.0f} min")

    with col_m4:
        # Show count of active critical actions (unresolved only)
        critical_count = len(unresolved_critical)
        st.metric("Critical Actions", critical_count)

    with col_m5:
        # ✅ Total Expected Cost:
        #   - If there are unresolved critical alerts → sum of their expected_cost
        #   - If all criticals are fixed → reset to 0
        if len(unresolved_critical) == 0:
            total_cost = 0
        else:
            total_cost = unresolved_critical["expected_cost"].sum()

        st.metric("Total Expected Cost", f"${total_cost:.0f}")

    # === MAIN CONTENT ===
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🖥️ Product On Process", "📋 Predictions", "📊 Analytics", "🔧 Maintenance Queue", "⚡ Stream History"]
    )

    with tab1:
        # === SINGLE MACHINE CURRENT STATUS ===

        # Get the most recent row
        latest_row = df_buf.sort_values("row_index", ascending=False).iloc[0]

        # Create Product ID
        machine_type = latest_row["raw_row"].get("Type", "?")
        product_id = f"Product #{latest_row['row_index']:04d}"
        tool_wear = latest_row["raw_row"].get("Tool wear [min]", 0)

        st.subheader(f"🏭 {product_id} • Type {machine_type}")
        st.caption(f"📊 Single-product production line • Tool wear: {tool_wear:.0f} min")

        # Action emoji and color
        action_emojis = {
            "critical_immediate": "🚨",
            "schedule_urgent": "⚠️",
            "schedule_soon": "⚡",
            "investigate": "🔍",
            "monitor": "👁️",
            "normal": "✅",
        }
        emoji = action_emojis.get(latest_row["maintenance_action"], "")

        # Big status banner with machine info
        status_text = (
            f"{emoji} **{latest_row['maintenance_action'].upper().replace('_', ' ')}**"
            f" - {latest_row['failure_mode']}"
        )

        if latest_row["maintenance_priority"] <= 2:
            st.error(status_text)
        elif latest_row["maintenance_priority"] <= 4:
            st.warning(status_text)
        else:
            st.success(status_text)

        # Key metrics in large display
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            quality_labels = {"L": "Low", "M": "Medium", "H": "High"}
            quality = quality_labels.get(machine_type, machine_type)
            st.metric(
                "Product Quality",
                f"Type {machine_type} ({quality})",
                delta=None,
                help="Product quality variant: L=Low, M=Medium, H=High",
            )

        with col2:
            st.metric(
                "Failure Probability",
                f"{latest_row['failure_proba']:.1%}",
                delta=None,
                help="Probability of machine failure",
            )

        with col3:
            st.metric(
                "Remaining Useful Life",
                f"{latest_row['rul_estimate']:.0f} min",
                delta=None,
                help="Estimated time until maintenance needed",
            )

        with col4:
            # 🔑 Use effective_expected_cost so NORMAL/MONITOR show $0
            st.metric(
                "Expected Cost",
                f"${latest_row['effective_expected_cost']:.0f}",
                delta=None,
                help="Expected cost of recommended action (0 if normal/monitor or resolved)",
            )

        # Detailed decision reasoning
        st.markdown("### 📋 Maintenance Decision")
        st.info(latest_row["maintenance_reasoning"])

        if latest_row["scheduled_time"]:
            st.markdown(f"**⏰ Scheduled Maintenance Time:** {latest_row['scheduled_time']}")

        # Sensor readings
        st.markdown("### 📊 Current Sensor Readings")
        raw_data = latest_row["raw_row"]

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.write(f"**Type:** {raw_data.get('Type', 'N/A')}")
            st.write(f"**Air Temp:** {raw_data.get('Air temperature [K]', 'N/A')} K")
            st.write(f"**Process Temp:** {raw_data.get('Process temperature [K]', 'N/A')} K")

        with col_b:
            st.write(f"**Rotational Speed:** {raw_data.get('Rotational speed [rpm]', 'N/A')} rpm")
            st.write(f"**Torque:** {raw_data.get('Torque [Nm]', 'N/A')} Nm")
            st.write(f"**Tool Wear:** {raw_data.get('Tool wear [min]', 'N/A')} min")

        with col_c:
            st.write(f"**Anomaly Score:** {latest_row['anomaly_score']:.3f}")
            st.write(f"**Anomaly Flag:** {'⚠️ YES' if latest_row['anomaly_flag'] else '✅ NO'}")
            st.write(f"**Energy Estimate:** {latest_row['energy_estimate']:.2f}")

        # Progress bars for key indicators
        st.markdown("### 📈 Key Indicators")

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            st.write("**Failure Probability**")
            st.progress(min(latest_row["failure_proba"], 1.0))

        with col_p2:
            st.write("**Anomaly Score**")
            st.progress(min(latest_row["anomaly_score"], 1.0))

        # Last update time
        st.caption(f"🕐 Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    with tab2:
        st.subheader("Latest Predictions")

        # Display table with color coding
        display_df = df_buf[
            [
                "row_index",
                "failure_mode",
                "failure_proba",
                "rul_estimate",
                "maintenance_action",
                "maintenance_priority",
                "expected_cost",
            ]
        ].sort_values("row_index", ascending=False).head(50)

        st.dataframe(
            display_df,
            column_config={
                "row_index": "Row",
                "failure_mode": "Failure Type",
                "failure_proba": st.column_config.NumberColumn("Fail Prob", format="%.2f"),
                "rul_estimate": st.column_config.NumberColumn("RUL (min)", format="%.0f"),
                "maintenance_action": "Action",
                "maintenance_priority": st.column_config.NumberColumn("Priority", format="%d"),
                "expected_cost": st.column_config.NumberColumn("Cost ($)", format="$%.2f"),
            },
            hide_index=True,
        )

    with tab3:
        st.subheader("Time Series Analytics")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Failure Probability Over Time**")
            st.line_chart(df_buf.set_index("row_index")["failure_proba"])

            st.write("**RUL Estimate Over Time**")
            st.line_chart(df_buf.set_index("row_index")["rul_estimate"])

        with col2:
            st.write("**Anomaly Score Over Time**")
            st.line_chart(df_buf.set_index("row_index")["anomaly_score"])

            st.write("**Expected Cost Over Time**")
            # Use effective cost for time series (normal/monitor & resolved → 0)
            st.line_chart(df_buf.set_index("row_index")["effective_expected_cost"])

        # Failure mode distribution
        st.write("**Failure Mode Distribution**")
        failure_dist = df_buf["failure_mode"].value_counts()
        st.bar_chart(failure_dist)

    with tab4:
        st.subheader("Maintenance Action Queue")

        # Group by maintenance action using effective cost (normal/monitor & resolved → 0)
        action_summary = (
            df_buf.groupby("maintenance_action")
            .agg(
                {
                    "row_index": "count",
                    "effective_expected_cost": "sum",
                    "maintenance_priority": "min",
                }
            )
            .rename(columns={"row_index": "count"})
            .sort_values("maintenance_priority")
        )

        st.dataframe(
            action_summary,
            column_config={
                "count": "Count",
                "effective_expected_cost": st.column_config.NumberColumn("Total Cost", format="$%.2f"),
                "maintenance_priority": "Priority Level",
            },
        )

        # Show detailed queue
        st.write("**Detailed Maintenance Queue (sorted by priority)**")
        queue_df = df_buf[
            [
                "row_index",
                "failure_mode",
                "maintenance_action",
                "maintenance_priority",
                "rul_estimate",
                "maintenance_reasoning",
                "scheduled_time",
            ]
        ].sort_values("maintenance_priority").head(20)

        for _, row in queue_df.iterrows():
            priority_emoji = {1: "🚨", 2: "⚠️", 3: "🔍", 4: "⚡", 5: "👁️", 6: "✅"}
            emoji = priority_emoji.get(row["maintenance_priority"], "")

            with st.expander(f"{emoji} Row {row['row_index']} - {row['maintenance_action'].upper()}"):
                st.write(f"**Failure Mode:** {row['failure_mode']}")
                st.write(f"**RUL:** {row['rul_estimate']:.0f} minutes")
                if row["scheduled_time"]:
                    st.write(f"**Scheduled:** {row['scheduled_time']}")
                st.info(row["maintenance_reasoning"])

    with tab5:
        st.subheader("Stream History")

        # Show latest 10 rows
        latest_rows = df_buf.sort_values("row_index", ascending=False).head(10)

        for _, row in latest_rows.iterrows():
            action_color = get_action_color(row["maintenance_action"])

            col_a, col_b, col_c = st.columns([1, 2, 2])

            with col_a:
                st.metric(f"Row {row['row_index']}", row["failure_mode"])

            with col_b:
                st.write(f"**Action:** {row['maintenance_action'].upper()}")
                st.progress(min(row["failure_proba"], 1.0), text=f"Fail Prob: {row['failure_proba']:.1%}")

            with col_c:
                st.write(
                    f"**RUL:** {row['rul_estimate']:.0f} min | "
                    f"**Cost:** ${row['effective_expected_cost']:.0f}"
                )
                st.caption(row["maintenance_reasoning"][:100] + "...")

            st.divider()


if __name__ == "__main__":
    main()
