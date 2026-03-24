import json
import threading
import os
from datetime import datetime
from collections import deque
from flask import Flask, render_template, jsonify
import paho.mqtt.client as mqtt

#  Config 
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT   = 1883
MQTT_TOPIC  = "iot/maks/sensors"
MAX_READINGS = 100
READINGS_FILE = "readings.json"
PORT = int(os.getenv("PORT", 5000))

app = Flask(__name__)

#  In-memory storage (deque auto-drops oldest over 100) 
readings = deque(maxlen=MAX_READINGS)

#  Load existing readings from file on startup 
def load_readings():
    try:
        with open(READINGS_FILE, 'r') as f:
            data = json.load(f)
            readings.extend(data)
            print(f"Loaded {len(data)} readings from file")
    except FileNotFoundError:
        print("No existing readings file, starting fresh")

#  Save readings to file 
def save_readings():
    with open(READINGS_FILE, 'w') as f:
        json.dump(list(readings), f, indent=2)

#  MQTT callbacks 
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"Connection failed: {reason_code}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        readings.append(data)
        save_readings()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Received: "
              f"temp={data.get('temperature')}  "
              f"hum={data.get('humidity')}  "
              f"pres={data.get('pressure')}")
    except Exception as e:
        print(f"Error processing message: {e}")

#  Flask routes 
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/readings')
def api_readings():
    return jsonify(list(readings))

@app.route('/api/latest')
def api_latest():
    if readings:
        return jsonify(readings[-1])
    return jsonify({})

#  Start MQTT in background thread 
def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()

if __name__ == '__main__':
    load_readings()
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()
    print(f"Starting Flask server at http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)