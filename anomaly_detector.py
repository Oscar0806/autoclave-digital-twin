import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
 
# Threshold limits (aerospace autoclave standards)
LIMITS = {
    "TC_max": 195.0,       # degC - any TC above = alarm
    "TC_min": 10.0,        # degC - any TC below = alarm
    "TC_spread": 8.0,      # degC - max difference between TCs
    "pressure_max": 8.0,   # bar
    "pressure_min": 0.5,   # bar (during cure hold phase)
    "vacuum_max": 300.0,   # mbar - above = bag leak
    "heat_rate_max": 3.0,  # degC/min - too fast = thermal shock
}
 
def check_thresholds(row):
    """Check one data row against limits. Returns alert list."""
    alerts = []
    tc_cols = [c for c in row.index if c.startswith("TC")]
    tc_vals = [row[c] for c in tc_cols]
    
    for col in tc_cols:
        if row[col] > LIMITS["TC_max"]:
            alerts.append(f"{col} HIGH: {row[col]:.1f} > "
                         f"{LIMITS['TC_max']} degC")
        if row[col] < LIMITS["TC_min"]:
            alerts.append(f"{col} LOW: {row[col]:.1f}")
    
    spread = max(tc_vals) - min(tc_vals)
    if spread > LIMITS["TC_spread"]:
        alerts.append(f"TC SPREAD: {spread:.1f} > "
                     f"{LIMITS['TC_spread']} degC")
    
    if row["pressure_bar"] > LIMITS["pressure_max"]:
        alerts.append(f"PRESSURE HIGH: {row['pressure_bar']:.2f}")
    if (row.get("phase") == "hold" and
        row["pressure_bar"] < LIMITS["pressure_min"]):
        alerts.append(f"PRESSURE LOW: {row['pressure_bar']:.2f}")
    
    if row["vacuum_mbar"] > LIMITS["vacuum_max"]:
        alerts.append(f"VACUUM LEAK: {row['vacuum_mbar']:.0f} mbar")
    
    return alerts
 
def train_anomaly_model(df):
    """Train Isolation Forest on sensor data."""
    feature_cols = ([c for c in df.columns if c.startswith("TC")]
                    + ["pressure_bar", "vacuum_mbar",
                       "heating_rate_degC_min"])
    X = df[feature_cols].values
    model = IsolationForest(
        contamination=0.1, random_state=42, n_estimators=100)
    model.fit(X)
    scores = model.decision_function(X)
    preds = model.predict(X)  # 1=normal, -1=anomaly
    return model, scores, preds
 
def analyze_cycle(df):
    """Full analysis: thresholds + ML."""
    all_alerts = []
    for _, row in df.iterrows():
        for a in check_thresholds(row):
            all_alerts.append({"minute": row["minute"], "alert": a})
    
    model, scores, preds = train_anomaly_model(df)
    df = df.copy()
    df["anomaly_score"] = scores
    df["is_anomaly_ml"] = preds == -1
    return df, pd.DataFrame(all_alerts), model
 
if __name__ == "__main__":
    from simulator import generate_cure_cycle
    df = generate_cure_cycle(6, anomaly_type="tc_drift")
    result, alerts, _ = analyze_cycle(df)
    print(f"Threshold alerts: {len(alerts)}")
    print(f"ML anomalies: {result['is_anomaly_ml'].sum()}")
    if len(alerts) > 0:
        print("Sample alerts:")
        print(alerts.head(5).to_string(index=False))