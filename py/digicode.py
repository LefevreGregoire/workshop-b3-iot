import threading
import time
import json
import logging
from datetime import datetime, timezone
import paho.mqtt.publish as publish


import requests
import psutil
import subprocess
import paho.mqtt.client as mqtt
import os
import cypher

os.environ['IDS_SECRET_KEY'] = 'JKp-xlgYazhuZZRf2R1c6_xj-6Jhz2kYXwEn8ydy5zc='

SERVER_URL = "http://192.168.50.171:5000"

def get_wifi_signal():
    try:
        output = subprocess.check_output("iwconfig wlan0 | grep -i quality", shell=True).decode()
        if "Signal level" in output: return output.split("Signal level=")[1].split(" ")[0]
    except: pass
    return "-100"

def telemetry_thread():
    while True:
        try:
            temp = 0.0
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
            except: pass
            payload = {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "ram_usage": psutil.virtual_memory().percent,
                "temp": temp,
                "wifi_signal": get_wifi_signal()
            }
            requests.post(f"{SERVER_URL}/api/telemetry/{DEVICE_NAME}", json=payload, timeout=2)
        except Exception: pass
        import time
        time.sleep(5)

def on_message(client, userdata, msg):
    global locked
    try:
        payload = json.loads(msg.payload.decode())
        action = payload.get("action")
        if action in ["LOCKDOWN", "LOCK", "TOGGLE"]:
            print("\n[!] COMMANDE DISTANTE: VERROUILLAGE FORCE !")
            locked = True
        elif action == "UNLOCK":
            print("\n[!] COMMANDE DISTANTE: DEVERROUILLAGE !")
            locked = False
    except: pass

def mqtt_listener_thread():
    client = mqtt.Client()
    client.username_pw_set('v-client', 'secret_iot_2026')
    client.on_message = on_message
    try:
        client.connect(BROKER_IP, 1883, 60)
        client.subscribe("cyberspace/command/global")
        client.subscribe(f"cyberspace/command/{DEVICE_NAME}")
        client.loop_forever()
    except Exception as e:
        print("Erreur listener:", e)


# Configuration
BROKER_IP = "192.168.50.171"
TOPIC = "cyberspace/capteurs/vessel1"
DEVICE_NAME = "sas-reacteur-01"
DEVICE_IP = "192.168.50.24"
SECRET_CODE = "2080" # Le code valide pour le Niveau 3

logging.basicConfig(level=logging.INFO, format='%(message)s')
locked = True

def create_alert(alert_type, message):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": DEVICE_NAME,
        "ip": DEVICE_IP,
        "type": alert_type,
        "message": message
    }

def publish_alert(alert):
    try:
        # CHIFFREMENT MILITAIRE ACTIF (Fernet + Timestamp)
        encrypted_payload = cypher.encrypt_message(DEVICE_NAME, alert)
        auth = {'username': 'v-client', 'password': 'secret_iot_2026'}
        publish.single(TOPIC, payload=encrypted_payload, hostname=BROKER_IP, port=1883, qos=1, auth=auth)
    except Exception as e:
        logging.error(f"[!] Erreur MQTT: {e}")

def pir_thread():
    try:
        from gpiozero import MotionSensor
        pir = MotionSensor(4)
        while True:
            pir.wait_for_motion()
            if locked:
                print("\n\n🚨 [ALERTE INTRUSION] Mouvement détecté dans la zone VERROUILLÉE !")
                publish_alert(create_alert("UNAUTHORIZED_ACCESS", "Intrusion physique détectée au niveau du réacteur (PIR)"))
                time.sleep(5) # Anti-spam
            pir.wait_for_no_motion()
    except Exception as e:
        print(f"\n[!] Capteur PIR non détecté (Démarrage sans capteur)")

def main():
    global locked
    threading.Thread(target=telemetry_thread, daemon=True).start()
    threading.Thread(target=mqtt_listener_thread, daemon=True).start()
    
    # Démarrer le capteur PIR en tâche de fond
    t = threading.Thread(target=pir_thread, daemon=True)
    t.start()
    
    print("="*60)
    print("🛸 TERMINAL D'ACCÈS - RÉACTEUR (Niveau 3) 🛸")
    print("="*60)
    
    while True:
        if locked:
            try:
                code = input("\n[🔒 VERROUILLÉ] Entrez le code d'accès : ")
                if code == SECRET_CODE:
                    print("\n✅ Code valide. Accès autorisé.")
                    locked = False
                    print("[🔓 DÉVERROUILLÉ] Le capteur de mouvement est désactivé temporairement.")
                    print("Le sas restera ouvert pendant 10 secondes...")
                    
                    time.sleep(10)
                    
                    locked = True
                    print("\n[🔒 VERROUILLÉ] Fermeture automatique du sas. Alarme réactivée.")
                else:
                    print(f"❌ Code invalide : {code}")
                    publish_alert(create_alert("AUTH_FAILURE", f"Tentative de code erroné : {code}"))
            except KeyboardInterrupt:
                print("\nArrêt du terminal.")
                break
            except EOFError:
                break
        else:
            time.sleep(1)

if __name__ == "__main__":
    main()
