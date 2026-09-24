import os
import sys
import threading
import json
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import cypher

# Clé de chiffrement partagée
os.environ['IDS_SECRET_KEY'] = 'JKp-xlgYazhuZZRf2R1c6_xj-6Jhz2kYXwEn8ydy5zc='

BROKER_IP = "192.168.50.171"
AUTH = {'username': 'v-client', 'password': 'secret_iot_2026'}
BASE_TOPIC = "cyberspace/chat/"

pseudo = input("Entrez votre pseudo pour la flotte : ").strip()
if not pseudo:
    pseudo = "Anonyme"
MY_TOPIC = f"{BASE_TOPIC}{pseudo}"

print(f"\n[+] Connexion sécurisée au réseau Inter-Vaisseau (MQTT AES-128)...")
print("[+] Écoute des communications...")
print("="*60)

def on_message(client, userdata, msg):
    # Ne pas s'afficher soi-même
    if msg.topic == MY_TOPIC:
        return
        
    try:
        raw_payload = msg.payload.decode('utf-8')
        decrypted = cypher.decrypt_message(raw_payload)
        
        if decrypted:
            sender = decrypted.get('device', 'Unknown')
            text = decrypted.get('data', {}).get('text', '')
            print(f"\r\033[96m[{sender}]\033[0m: {text}")
        else:
            print(f"\r\033[91m[!] Message intercepté illisible (Clé invalide ou expiré)\033[0m")
            
        # Réafficher le prompt
        sys.stdout.write(f"\rVous: ")
        sys.stdout.flush()
    except Exception as e:
        pass

def mqtt_listener():
    client = mqtt.Client()
    client.username_pw_set(AUTH['username'], AUTH['password'])
    client.on_message = on_message
    try:
        client.connect(BROKER_IP, 1883, 60)
        client.subscribe(BASE_TOPIC + "#")
        client.loop_forever()
    except Exception as e:
        print(f"Erreur de connexion : {e}")

# Démarrer l'écoute en arrière-plan
threading.Thread(target=mqtt_listener, daemon=True).start()

# Boucle d'envoi
while True:
    try:
        msg_text = input("\rVous: ")
        if not msg_text.strip():
            continue
            
        payload = {"text": msg_text}
        encrypted_token = cypher.encrypt_message(pseudo, payload)
        
        publish.single(MY_TOPIC, payload=encrypted_token, hostname=BROKER_IP, port=1883, auth=AUTH)
    except KeyboardInterrupt:
        print("\nDéconnexion...")
        break
    except EOFError:
        break
