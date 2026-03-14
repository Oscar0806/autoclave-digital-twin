import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from simulator import generate_cure_cycle
from anomaly_detector import analyze_cycle, check_thresholds, LIMITS
 
# ── PAGE CONFIG ──
st.set_page_config(
    page_title="Autoclave Digital Twin",
    page_icon="\u2708\uFE0F",
    layout="wide"
)
 
st.title("\u2708\uFE0F Composite Autoclave Digital Twin")
st.markdown(
    "**Real-time monitoring dashboard for CFRP cure cycle "
    "\u2013 Airbus Stade concept**"
)
st.divider()
 
# ── SIDEBAR CONTROLS ──
st.sidebar.header("\u2699\uFE0F Cycle Selection")
cycle_type = st.sidebar.selectbox(
    "Select cycle type:",
    ["Normal Cure Cycle",
     "Anomaly: Thermocouple Drift",
     "Anomaly: Pressure Leak",
     "Anomaly: Heater Failure",
     "Anomaly: Vacuum Bag Leak"]
)
anomaly_map = {
    "Normal Cure Cycle": None,
    "Anomaly: Thermocouple Drift": "tc_drift",
    "Anomaly: Pressure Leak": "pressure_leak",
    "Anomaly: Heater Failure": "heater_fail",
    "Anomaly: Vacuum Bag Leak": "vacuum_loss",
}
cycle_id = st.sidebar.number_input("Cycle ID:", 1, 100, 1)
sim_minute = st.sidebar.slider(
    "Simulation time (minute):", 0, 299, 299,
    help="Drag to replay the cure cycle up to this minute"
)
 
# ── GENERATE + ANALYZE ──
anomaly = anomaly_map[cycle_type]
df_full = generate_cure_cycle(cycle_id, anomaly_type=anomaly)
df = df_full[df_full["minute"] <= sim_minute].copy()
df_analyzed, alerts_df, _ = analyze_cycle(df)
latest = df_analyzed.iloc[-1]
 
# ── KPI CARDS (top row) ──
st.subheader("\U0001f4ca Live Status")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    avg_t = np.mean([latest[f"TC{i}_degC"] for i in range(1, 7)])
    st.metric("Avg Temp",
              f"{avg_t:.1f} \u00B0C",
              f"{latest['heating_rate_degC_min']:.2f} \u00B0C/min")
with col2:
    st.metric("Pressure", f"{latest['pressure_bar']:.2f} bar")
with col3:
    vac_ok = latest["vacuum_mbar"] < 300
    st.metric("Vacuum",
              f"{latest['vacuum_mbar']:.0f} mbar",
              "OK" if vac_ok else "LEAK!",
              delta_color="normal" if vac_ok else "inverse")
with col4:
    st.metric("Phase", latest["phase"].replace("_", " ").title())
with col5:
    st.metric("Progress", f"{sim_minute / 299 * 100:.0f}%")
 
# ── ALERT PANEL ──
current_alerts = check_thresholds(latest)
if current_alerts:
    st.error(
        f"\u26A0\uFE0F **{len(current_alerts)} ACTIVE ALERTS**"
    )
    for a in current_alerts:
        st.warning(f"\u26A0\uFE0F {a}")
elif anomaly:
    st.info(
        "\U0001f50d Monitoring anomaly cycle \u2013 "
        "drag the time slider to see alerts appear"
    )
else:
    st.success("\u2705 All parameters within limits")
 
st.divider()
 
# ── TEMPERATURE CHART ──
st.subheader("\U0001f321\uFE0F Temperature Profile (6 Zones)")
fig_t = go.Figure()
colors = ["#E74C3C","#3498DB","#2ECC71","#F39C12","#9B59B6","#1ABC9C"]
for i in range(6):
    fig_t.add_trace(go.Scatter(
        x=df_analyzed["minute"],
        y=df_analyzed[f"TC{i+1}_degC"],
        name=f"TC{i+1}",
        line=dict(color=colors[i], width=2)))
fig_t.add_hline(y=LIMITS["TC_max"], line_dash="dash",
                line_color="red",
                annotation_text=f"Max {LIMITS['TC_max']}\u00B0C")
fig_t.add_hline(y=180, line_dash="dot", line_color="gray",
                annotation_text="Target 180\u00B0C")
fig_t.update_layout(xaxis_title="Time (min)",
                    yaxis_title="Temperature (\u00B0C)",
                    height=400, template="plotly_white",
                    legend=dict(orientation="h", y=1.12))
st.plotly_chart(fig_t, use_container_width=True)
 
# ── PRESSURE + VACUUM (side by side) ──
left, right = st.columns(2)
with left:
    st.subheader("\U0001f527 Pressure")
    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(
        x=df_analyzed["minute"],
        y=df_analyzed["pressure_bar"],
        name="Pressure", fill="tozeroy",
        line=dict(color="#3498DB", width=2)))
    fig_p.add_hline(y=LIMITS["pressure_max"], line_dash="dash",
                    line_color="red",
                    annotation_text=f"Max {LIMITS['pressure_max']} bar")
    fig_p.update_layout(xaxis_title="Time (min)",
                        yaxis_title="Pressure (bar)",
                        height=300, template="plotly_white")
    st.plotly_chart(fig_p, use_container_width=True)
 
with right:
    st.subheader("\U0001f32c\uFE0F Vacuum")
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(
        x=df_analyzed["minute"],
        y=df_analyzed["vacuum_mbar"],
        name="Vacuum", fill="tozeroy",
        line=dict(color="#2ECC71", width=2)))
    fig_v.add_hline(y=LIMITS["vacuum_max"], line_dash="dash",
                    line_color="red",
                    annotation_text=f"Limit {LIMITS['vacuum_max']} mbar")
    fig_v.update_layout(xaxis_title="Time (min)",
                        yaxis_title="Vacuum (mbar)",
                        height=300, template="plotly_white")
    st.plotly_chart(fig_v, use_container_width=True)
 
# ── HEATMAP ──
st.subheader("\U0001f5fa\uFE0F Temperature Zone Heatmap")
tc_cols = [f"TC{i}_degC" for i in range(1, 7)]
fig_h = px.imshow(
    df_analyzed[tc_cols].values.T,
    labels=dict(x="Time (min)", y="Thermocouple",
                color="Temp (\u00B0C)"),
    x=df_analyzed["minute"].values,
    y=[f"TC{i}" for i in range(1, 7)],
    color_continuous_scale="RdYlBu_r", aspect="auto")
fig_h.update_layout(height=250)
st.plotly_chart(fig_h, use_container_width=True)
 
# ── ML ANOMALY CHART ──
st.subheader("\U0001f916 ML Anomaly Detection (Isolation Forest)")
fig_a = go.Figure()
fig_a.add_trace(go.Scatter(
    x=df_analyzed["minute"],
    y=df_analyzed["anomaly_score"],
    name="Anomaly Score",
    line=dict(color="#8E44AD", width=2)))
anom_pts = df_analyzed[df_analyzed["is_anomaly_ml"]]
fig_a.add_trace(go.Scatter(
    x=anom_pts["minute"],
    y=anom_pts["anomaly_score"],
    mode="markers", name="ML Anomaly",
    marker=dict(color="red", size=6, symbol="x")))
fig_a.add_hline(y=0, line_dash="dash", line_color="gray",
                annotation_text="Decision boundary")
fig_a.update_layout(xaxis_title="Time (min)",
                    yaxis_title="Anomaly Score",
                    height=300, template="plotly_white")
st.plotly_chart(fig_a, use_container_width=True)
 
# ── ALERT LOG ──
if len(alerts_df) > 0:
    st.subheader("\U0001f4cb Alert Log")
    st.dataframe(alerts_df, use_container_width=True, height=200)
 
# ── FOOTER ──
st.divider()
st.caption(
    "Digital Twin Dashboard for Composite Autoclave Curing | "
    "Concept for Airbus Stade CFRP Production | "
    "Built by Oscar Vincent Dbritto"
    
)
