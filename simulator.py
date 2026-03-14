import numpy as np
import pandas as pd
from datetime import datetime, timedelta
 
def generate_cure_cycle(cycle_id=1, anomaly_type=None):
    """Generate one complete autoclave cure cycle.
    Standard aerospace CFRP cure: ramp to 180C, hold 120min, cool.
    """
    np.random.seed(cycle_id)
    
    # Phase durations (minutes)
    ramp_up = 90     # heat from 20C to 180C
    hold = 120       # hold at 180C (cure)
    cool_down = 90   # cool from 180C to 60C
    total = ramp_up + hold + cool_down  # 300 minutes
    
    times = [datetime(2026, 3, 1, 8, 0) + timedelta(minutes=i)
             for i in range(total)]
    
    # Base temperature profile
    base_temp = np.zeros(total)
    for i in range(total):
        if i < ramp_up:
            base_temp[i] = 20 + (180 - 20) * (i / ramp_up)
        elif i < ramp_up + hold:
            base_temp[i] = 180
        else:
            t_cool = i - ramp_up - hold
            base_temp[i] = 180 - (180 - 60) * (t_cool / cool_down)
    
    # 6 thermocouples with zone offsets + noise
    tc_offsets = [0, -2, 1.5, -1, 2.5, -0.5]
    tc_data = {}
    for j in range(6):
        noise = np.random.normal(0, 0.5, total)
        tc_data[f"TC{j+1}_degC"] = base_temp + tc_offsets[j] + noise
    
    # Pressure (bar): ramp to 7 bar in 30min, hold, then release
    pressure = np.zeros(total)
    for i in range(total):
        if i < 30:
            pressure[i] = 1 + (7 - 1) * (i / 30)
        elif i < ramp_up + hold:
            pressure[i] = 7.0
        else:
            t_cool = i - ramp_up - hold
            pressure[i] = 7.0 - (7.0 - 1.0) * (t_cool / cool_down)
    pressure += np.random.normal(0, 0.05, total)
    
    # Vacuum (mbar): target < 200 mbar
    vacuum = np.full(total, 150.0) + np.random.normal(0, 10, total)
    
    # Heating rate (degC/min)
    heating_rate = np.gradient(base_temp)
    heating_rate += np.random.normal(0, 0.02, total)
    
    # ── INJECT ANOMALIES ──
    if anomaly_type == "tc_drift":
        # TC3 drifts high starting at minute 100
        tc_data["TC3_degC"][100:] += np.linspace(0, 15, total - 100)
    elif anomaly_type == "pressure_leak":
        # Slow pressure drop starting at minute 60
        leak = np.zeros(total)
        leak[60:] = np.linspace(0, 2.5, total - 60)
        pressure -= leak
    elif anomaly_type == "heater_fail":
        # Zone 2 heater fails at minute 50
        tc_data["TC2_degC"][50:80] -= np.linspace(0, 25, 30)
        tc_data["TC2_degC"][80:] -= 25
    elif anomaly_type == "vacuum_loss":
        # Vacuum bag leak at minute 120
        vacuum[120:] += np.linspace(0, 300, total - 120)
    
    # Build DataFrame
    df = pd.DataFrame({
        "timestamp": times,
        "minute": range(total),
        "cycle_id": cycle_id,
        **tc_data,
        "pressure_bar": pressure,
        "vacuum_mbar": vacuum,
        "heating_rate_degC_min": heating_rate,
        "phase": ["ramp_up" if i < ramp_up
                   else "hold" if i < ramp_up + hold
                   else "cool_down" for i in range(total)],
    })
    return df
 
if __name__ == "__main__":
    df = generate_cure_cycle(1, anomaly_type=None)
    df.to_csv("cure_data.csv", index=False)
    print(f"Generated {len(df)} data points")
    print(f"Columns: {list(df.columns)}")
    print(f"Saved to cure_data.csv")
