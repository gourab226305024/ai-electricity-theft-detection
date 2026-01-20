from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.data_generator import generate_data, get_live_consumption
from backend.anomaly_detector import detect_anomalies

app = FastAPI()

# ✅ ADD CORS FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ DEFINE API ROUTES FIRST (before static files)
CURRENT_MODE = "normal"

@app.get("/generate/{mode}")
def generate(mode: str):
    global CURRENT_MODE
    CURRENT_MODE = mode
    if mode == "normal":
        generate_data(theft=False)
    else:
        generate_data(theft=True)
    return {"mode": mode}

@app.get("/detect")
def detect():
    """
    Get live consumption from potentiometer and calculate risk score
    """
    try:
        # Get live potentiometer reading
        live_consumption = get_live_consumption(mode=CURRENT_MODE)
        
        # Calculate risk score based on consumption
        risk_score = calculate_risk(live_consumption)
        anomaly = 1 if risk_score > 70 else 0
        
        # Generate reason text
        if anomaly == 1:
            reason = f"⚠️ Suspicious consumption detected: {live_consumption:.2f} kWh (Expected: 20-40 kWh)"
        else:
            reason = f"✓ Normal consumption: {live_consumption:.2f} kWh"
        
        return {
            "consumption": round(live_consumption, 2),
            "risk_score": risk_score,
            "anomaly": anomaly,
            "reason": reason
        }
    except Exception as e:
        print(f"Error in detect endpoint: {e}")
        return {
            "consumption": 0.0,
            "risk_score": 0,
            "anomaly": 0,
            "reason": f"Error: {str(e)}"
        }

def calculate_risk(consumption):
    """
    Calculate risk score based on consumption value
    
    Args:
        consumption: Current consumption value in kWh
    
    Returns:
        int: Risk score 0-100
    """
    expected_min = 20
    expected_max = 40
    
    if consumption < expected_min:
        # Below normal = potential theft
        deviation = expected_min - consumption
        risk = min(80, (deviation / expected_min) * 100)
    elif consumption > expected_max:
        # Above normal = overconsumption
        deviation = consumption - expected_max
        risk = min(60, (deviation / expected_max) * 50)
    else:
        # Normal range = low risk
        risk = 10
    
    return int(risk)

# ✅ THEN SERVE STATIC FILES
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

# Mount frontend folder
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
