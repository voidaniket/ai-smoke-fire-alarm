import serial
import time
import requests
import numpy as np
from sklearn.ensemble import IsolationForest
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# --- CONFIGURATION ---
PORT = '/dev/ttyACM0'  # Your Arduino port
BAUD = 9600

def send_phone_alert(message):
    """Sends an instant push notification / message to your phone via Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"🚨 SMART ALARM SYSTEM 🚨\n\n{message}"
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("📱 Phone alert sent successfully!")
        else:
            print("❌ Failed to send phone alert.")
    except Exception as e:
        print(f"Error sending alert: {e}")

# --- CONNECT TO ARDUINO ---
print(f"Connecting to Arduino on {PORT}...")
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

# --- AI TRAINING PHASE ---
print("🤖 AI Calibration: Collecting 10 seconds of baseline room air data...")
baseline_data = []
start_time = time.time()

while time.time() - start_time < 10:
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if "Smoke/Gas:" in line:
            try:
                parts = line.split('|')
                gas = int(parts[0].split(':')[1].strip())
                flame = int(parts[1].split(':')[1].strip())
                baseline_data.append([gas, flame])
            except ValueError:
                pass

if len(baseline_data) < 5:
    baseline_data = [[300, 900], [310, 895], [305, 902], [295, 905]]

# Train Isolation Forest AI Model
model = IsolationForest(contamination=0.03, random_state=42)
model.fit(np.array(baseline_data))
print("✅ AI Model successfully trained on your room's baseline!")
print("🚀 Live AI Monitoring Active. Press Ctrl+C to stop.")

alert_cooldown = 0  # Prevents spamming your phone every single second

try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if "Smoke/Gas:" in line:
                try:
                    parts = line.split('|')
                    gas = int(parts[0].split(':')[1].strip())
                    flame = int(parts[1].split(':')[1].strip())
                    
                    # AI Anomaly Prediction
                    current_reading = np.array([[gas, flame]])
                    prediction = model.predict(current_reading)
                    
                    # If AI detects an anomaly (-1) or thresholds are crossed
                    if prediction[0] == -1 or gas > 400 or flame < 500:
                        print(f"🚨 AI ANOMALY/DANGER DETECTED! Smoke: {gas}, Flame: {flame}")
                        
                        # Send phone alert (with a 30-second cooldown so it doesn't flood your phone)
                        if time.time() - alert_cooldown > 30:
                            send_phone_alert(f"Danger detected in your room!\nSmoke Level: {gas}\nFlame Value: {flame}")
                            alert_cooldown = time.time()
                    else:
                        print(f"Status Normal -> Smoke: {gas}, Flame: {flame}")
                except Exception:
                    pass
except KeyboardInterrupt:
    ser.close()
    print("\n🛑 Monitoring stopped. Safe disconnecting.")