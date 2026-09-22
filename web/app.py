from flask import Flask, jsonify, send_from_directory
import paho.mqtt.client as mqtt
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')

devices = [
    {"id": "ESP8266-SAIN", "ip": "10.42.0.100", "status": "ONLINE", "last_seen": datetime.now().isoformat()}
]
logs = [
    {"timestamp": datetime.now().isoformat(), "device": "SYSTEM", "severity": "INFO", "type": "STARTUP", "message": "Serveur Flask initialisé et en écoute.", "resolved": True}
]

def on_connect(client, userdata, flags, rc):
    print("✅ Connecté au broker MQTT du Raspberry Pi !")
    client.subscribe("cyberspace/capteurs")

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"📥 Nouveau message ({msg.topic}) : {payload}")
    
    logs.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "device": "Capteur",
        "severity": "WARN", 
        "type": "MQTT_INBOUND",
        "message": payload,
        "resolved": False
    })

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect("10.42.0.246", 1883, 60)
    client.loop_start()
except Exception as e:
    print(f"⚠️ Impossible de joindre le broker: {e}")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/devices')
def api_devices():
    return jsonify(devices)

@app.route('/api/logs')
def api_logs():
    return jsonify(logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
