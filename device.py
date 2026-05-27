import time
import random
import requests
import json

API_URL = "http://localhost:8000/api/telemetry"
DEVICE_ID = "STM32-ASIC-TEST-01"

def generate_parametric_sweep():
    """ Simulates a variable voltage and frequency step-test sweep. """
    voltage = round(random.uniform(1.2, 3.3), 2)
    frequency_mhz = random.choice([100, 200, 400, 800])
    
    # Simulate a component failure if voltage drops too low at high frequency
    status = "STABLE"
    if voltage < 1.8 and frequency_mhz >= 400:
        status = "DEFECT_ALERT"
        
    return {
        "device_id": DEVICE_ID,
        "timestamp": time.time(),
        "voltage_v": voltage,
        "frequency_mhz": frequency_mhz,
        "temperature_c": round(random.uniform(30.0, 75.0), 1),
        "status": status
    }

if __name__ == "__main__":
    print(f"Starting hardware telemetry stream for {DEVICE_ID}...")
    while True:
        payload = generate_parametric_sweep()
        try:
            response = requests.post(API_URL, json=payload, timeout=2)
            print(f"[Sent] Status: {payload['status']} | Response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[Error] Failed to connect to Ingestion Server: {e}")
        
        time.sleep(1.0) # 1Hz streaming telemetry