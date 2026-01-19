import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import serial
import time
import os

# Create data folder if it doesn't exist
os.makedirs("data", exist_ok=True)

# ============================================
# POTENTIOMETER CONFIGURATION
# ============================================

HARDWARE_TYPE = "arduino"  # Options: "arduino", "simulation"
ARDUINO_PORT = "COM8"      # Change to your port (COM3, COM4, /dev/ttyACM0, etc)
ARDUINO_BAUD = 9600

# Global variable to store serial connection
arduino_connection = None

# ============================================
# POTENTIOMETER READER
# ============================================

def init_arduino():
    """Initialize Arduino connection"""
    global arduino_connection
    try:
        arduino_connection = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
        time.sleep(2)
        print(f"✅ Arduino connected on {ARDUINO_PORT}")
        return True
    except Exception as e:
        print(f"⚠️ Arduino connection failed: {e}")
        print("Falling back to simulation mode")
        return False

from collections import deque

# Moving average buffer
reading_buffer = deque(maxlen=5)

def read_potentiometer():
    """
    Read potentiometer value from Arduino with low latency and smoothing
    Returns consumption value (0-50 kWh)
    """
    global arduino_connection
    
    if HARDWARE_TYPE == "simulation":
        # Simulate slight noise
        val = np.random.uniform(0, 50)
        reading_buffer.append(val)
        return round(sum(reading_buffer) / len(reading_buffer), 2)
    
    try:
        if arduino_connection:
            if arduino_connection.in_waiting > 0:
                # Read ALL bytes to clear buffer and get only the absolute latest data
                # This fixes the "lag" where code processes old buffered data
                raw_data = arduino_connection.read_all().decode(errors='ignore')
                lines = raw_data.strip().split('\n')
                
                # Get the last valid line
                for line in reversed(lines):
                    line = line.strip()
                    if line.isdigit():
                        latest_value = int(line)
                        
                        # Convert to kWh
                        consumption = (latest_value / 1023.0) * 50.0
                        
                        # Add to buffer for smoothing
                        reading_buffer.append(consumption)
                        
                        # Return smoothed average
                        smoothed_val = sum(reading_buffer) / len(reading_buffer)
                        print(f"Raw: {latest_value} -> Smoothed: {smoothed_val:.2f}")
                        return round(smoothed_val, 2)
            
            # If no new data, return the last known average (or 0 if empty)
            if reading_buffer:
                return round(sum(reading_buffer) / len(reading_buffer), 2)
                
    except Exception as e:
        print(f"Error reading potentiometer: {e}")
    
    return 0.0
# ============================================
# ORIGINAL DATA GENERATION FUNCTION
# ============================================

def generate_data(theft=False):
    """
    Generate consumption data from potentiometer or simulation
    
    Args:
        theft: If True, simulate theft scenario (reduce readings)
    """
    global arduino_connection
    
    # Initialize Arduino if not already connected
    if arduino_connection is None and HARDWARE_TYPE == "arduino":
        init_arduino()
    
    records = []
    time = datetime.now()
    base = 3.0

    for i in range(60):
        # Read from potentiometer if available
        if HARDWARE_TYPE == "arduino" and arduino_connection:
            try:
                pot_value = read_potentiometer()
                if pot_value > 0:
                    # Use potentiometer reading
                    usage = pot_value / 10  # Scale down to match original range
                else:
                    # Fallback to original logic
                    if theft and i > 40:
                        usage = base * 0.3   # 🔴 BIG DROP
                    else:
                        usage = base + np.random.normal(0, 0.2)
            except:
                # Fallback if read fails
                if theft and i > 40:
                    usage = base * 0.3
                else:
                    usage = base + np.random.normal(0, 0.2)
        else:
            # Original simulation logic
            if theft and i > 40:
                usage = base * 0.3   # 🔴 BIG DROP
            else:
                usage = base + np.random.normal(0, 0.2)

        usage = round(max(0.4, usage), 2)
        records.append([time, usage])
        time += timedelta(minutes=15)

    df = pd.DataFrame(records, columns=["timestamp", "consumption"])
    try:
        df.to_csv("data/meter_data.csv", index=False)
        print(f"✅ Data generated: {len(records)} records | Mode: {'THEFT' if theft else 'NORMAL'}")
    except Exception as e:
        print(f"⚠️ Warning: Could not save CSV: {e}")
        print(f"✅ Data generated: {len(records)} records | Mode: {'THEFT' if theft else 'NORMAL'}")

# ============================================
# LIVE POTENTIOMETER READING (for dashboard)
# ============================================

def get_live_consumption():
    """
    Get current consumption from potentiometer
    Use this in your /detect endpoint for real-time readings
    """
    global arduino_connection
    
    if arduino_connection is None and HARDWARE_TYPE == "arduino":
        init_arduino()
    
    if HARDWARE_TYPE == "arduino" and arduino_connection:
        return read_potentiometer()
    else:
        # Return random value if in simulation
        return round(np.random.uniform(0, 50), 2)

# ============================================
# TEST FUNCTION
# ============================================

def test_potentiometer():
    """Test potentiometer connection and readings"""
    print("Testing potentiometer connection...")
    
    if HARDWARE_TYPE == "arduino":
        if not init_arduino():
            print("Could not connect to Arduino. Using simulation mode.")
            return
        
        print("\nReading 10 values:")
        for i in range(10):
            value = read_potentiometer()
            print(f"  Reading {i+1}: {value:.2f} kWh")
            time.sleep(0.5)
    else:
        print("Simulation mode - generating random values:")
        for i in range(10):
            value = get_live_consumption()
            print(f"  Reading {i+1}: {value:.2f} kWh")
            time.sleep(0.1)

# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    # Test potentiometer
    test_potentiometer()
    
    # Generate normal data
    print("\n--- Generating NORMAL data ---")
    generate_data(theft=False)
    
    # Generate theft scenario data
    print("\n--- Generating THEFT data ---")
    generate_data(theft=True)