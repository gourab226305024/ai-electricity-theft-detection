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

st.subheader("Electricity Consumption Pattern")
st.line_chart(df["consumption"])

latest = df.iloc[-1]["anomaly"]

if latest == -1:
    st.error("⚠️ Suspicious Consumption Detected (Possible Theft)")
else:
    st.success("✅ Normal Consumption Pattern")

st.subheader("Recent Smart Meter Data")
st.dataframe(df.tail(10))
