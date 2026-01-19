import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.anomaly_detector import detect_anomalies
from backend.data_generator import generate_data

st.set_page_config(page_title="Electricity Theft Detection", layout="wide")

st.title("⚡ AI-Based Electricity Theft Detection System")

st.sidebar.header("Simulation Control")

mode = st.sidebar.radio(
    "Select Consumption Mode",
    ("Normal Usage", "Theft Scenario")
)

if st.sidebar.button("Generate Data"):
    if mode == "Normal Usage":
        generate_data(theft=False)
    else:
        generate_data(theft=True)
    st.success("Smart meter data generated")

df = detect_anomalies()


import time

st.subheader("Electricity Consumption Pattern")
st.line_chart(df["consumption"])

latest = df.iloc[-1]["anomaly"]

if latest == -1:
    st.error("⚠️ Suspicious Consumption Detected (Possible Theft)")
else:
    st.success("✅ Normal Consumption Pattern")

st.subheader("Recent Smart Meter Data")
st.dataframe(df.tail(10))

# --- LIVE MONITORING MODE ---
st.divider()
st.subheader("🔴 Live Hardware Monitor")

if st.checkbox("Enable Live Data Stream", value=False):
    live_placeholder = st.empty()
    
    # Run loop to fetch data continuously
    while True:
        try:
            # Fetch latest reading from backend directly
            # Note: In a production app, this should be an API call to avoid blocking, 
            # but for this local prototype, direct import is faster/easier.
            from backend.data_generator import get_live_consumption
            from backend.main import calculate_risk # Re-import to get fresh state if needed
            
            # Use the optimized non-blocking reader we just fixed
            current_val = get_live_consumption()
            
            # Simple risk logic (copying from main.py for display speed)
            expected_min = 20
            expected_max = 40
            risk_score = 0
            
            if current_val < expected_min:
                risk = min(80, ((expected_min - current_val) / expected_min) * 100)
            elif current_val > expected_max:
                risk = min(60, ((current_val - expected_max) / expected_max) * 50)
            else:
                risk = 10
            
            status_color = "green"
            status_text = "NORMAL"
            if risk > 70:
                status_color = "red" 
                status_text = "THEFT DETECTED"
            elif risk > 40:
                status_color = "orange"
                status_text = "WARNING"
                
            with live_placeholder.container():
                col1, col2, col3 = st.columns(3)
                col1.metric("Live Consumption", f"{current_val:.2f} kWh")
                col2.metric("Risk Score", f"{int(risk)}/100")
                col3.markdown(f":{status_color}[**{status_text}**]")
                
                # Add a mini chart for last few readings if we wanted, 
                # but valid metrics are fastest for 'real-time' feel.
                
            # Sleep very strictly to prevent UI freeze, but fast enough for smooth updates
            time.sleep(0.1) 
            
        except Exception as e:
            st.error(f"Error in live loop: {e}")
            break
