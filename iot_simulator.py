import time
import json
import random

def generate_telemetry_payload(vehicle_code: str):
    """Giả lập gói tin JSON viễn thám từ phương tiện."""
    return {
        "vehicle_code": vehicle_code,
        "battery_level": round(random.uniform(15.0, 100.0), 2),
        "latitude": round(10.8700 + random.uniform(-0.005, 0.005), 6),
        "longitude": round(106.8000 + random.uniform(-0.005, 0.005), 6),
        "speed_kmh": round(random.uniform(0.0, 35.0), 1),
        "is_locked": True,
        "timestamp": int(time.time())
    }

if __name__ == "__main__":
    print("=== STARTING IOT TELEMETRY SIMULATOR ===")
    for i in range(1, 4):
        payload = generate_telemetry_payload(f"VEH_{i:03d}")
        print(f"[IoT Gateway Direct] Received: {json.dumps(payload, indent=2)}")
        time.sleep(1)