import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_anomalies():
    df = pd.read_csv("data/meter_data.csv")

    # Safety check
    if len(df) < 5:
        df["risk_score"] = 0
        df["final_anomaly"] = 1
        df["reason"] = "Insufficient data"
        return df

    # ---------- ML PART ----------
    model = IsolationForest(contamination=0.2, random_state=42)
    df["ml_anomaly"] = model.fit_predict(df[["consumption"]])

    # ---------- STATISTICAL PART ----------
    recent_avg = df["consumption"].rolling(window=5).mean()
    last_value = df["consumption"].iloc[-1]
    avg_value = recent_avg.iloc[-1]

    drop_percent = ((avg_value - last_value) / avg_value) * 100

    # ---------- RISK SCORE ----------
    risk_score = 0
    reason = "Normal usage"

    if drop_percent > 20:
        risk_score = 60
        reason = "Moderate drop in consumption"

    if drop_percent > 40:
        risk_score = 80
        reason = "Sudden significant drop detected"

    if df["ml_anomaly"].iloc[-1] == -1:
        risk_score = max(risk_score, 70)
        reason = "Anomalous consumption pattern"

    # Final decision
    final_anomaly = -1 if risk_score >= 70 else 1

    df.at[df.index[-1], "risk_score"] = risk_score
    df.at[df.index[-1], "final_anomaly"] = final_anomaly
    df.at[df.index[-1], "reason"] = reason

    return df
