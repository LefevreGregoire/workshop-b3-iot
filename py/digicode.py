import threading
import time
import json
import logging
from datetime import datetime, timezone
import paho.mqtt.publish as publish
from gpiozero import MotionSensor

# Configuration
BROKER_IP = "192.168.50.171"
TOPIC = "cyberspace/capteurs/vessel1"
DEVICE_NAME = "sas-reacteur-01"
DEVICE_IP = "10.42.0.188"
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
        publish.single(TOPIC, payload=json.dumps(alert), hostname=BROKER_IP, port=1883, qos=1)
    except Exception as e:
        logging.error(f"[!] Erreur MQTT: {e}")

def pir_thread():
    try:
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
