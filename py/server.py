from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
from pathlib import Path
import os
import json
import threading

import paho.mqtt.client as mqtt

from ids import AutomaticIDS

try:
    from isolation import (
        handle_alert,
        is_isolated,
        restore_device as restore_isolated_device
    )
except ImportError:
    handle_alert = None
    is_isolated = None
    restore_isolated_device = None

    print(
        "⚠️ isolation.py introuvable."
        " L'isolation automatique sera désactivée."
    )


# ============================================================
# IMPORT CLASIFY
# ============================================================
# Classification automatique de la sévérité (LOG/WARN/CRITICAL)
# quand l'appelant n'en fournit pas, et tri des logs par risque.
# ============================================================

try:
    from classify import classify_alert, sort_by_severity
except ImportError:
    classify_alert = None
    sort_by_severity = None

    print(
        "⚠️ classify.py introuvable."
        " La classification automatique sera désactivée."
    )


# ============================================================
# IMPORT CYPHER
# ============================================================
# Permet aux devices d'envoyer un heartbeat chiffré
# ({"token": "..."}) au lieu d'un JSON en clair. Nécessite la
# variable d'environnement IDS_SECRET_KEY côté serveur.
# ============================================================

try:
    from cypher import decrypt_message as decrypt_heartbeat_token
except ImportError:
    decrypt_heartbeat_token = None

    print(
        "⚠️ cypher.py introuvable."
        " Les heartbeats chiffrés seront refusés."
    )


# ============================================================
# IMPORT WATCHDOG
# ============================================================
# Surveille en continu les devices qui n'envoient plus de
# heartbeat, et rappelle les alertes CRITICAL non résolues.
# ============================================================

try:
    import watchdog as watchdog_module
except ImportError:
    watchdog_module = None

    print(
        "⚠️ watchdog.py introuvable."
        " La surveillance automatique des devices sera désactivée."
    )


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = Flask(
    __name__,
    static_folder=str(WEB_DIR),
    static_url_path=""
)

ids = AutomaticIDS()

devices = {}
telemetry_data = {}
logs = []
data_lock = threading.Lock()


# ============================================================
# CONFIGURATION
# ============================================================

MQTT_BROKER = os.getenv(
    "MQTT_BROKER",
    "127.0.0.1"
)

MQTT_PORT = int(
    os.getenv(
        "MQTT_PORT",
        "1883"
    )
)

MQTT_TOPIC = os.getenv(
    "MQTT_TOPIC",
    "cyberspace/capteurs/#"
)

MQTT_CLIENT_ID = os.getenv(
    "MQTT_CLIENT_ID",
    "inter-vessel-security-center"
)

# Modes :
#
# observe -> détecte et log, aucune isolation
# notify  -> détecte et log, aucune isolation
# isolate -> CRITICAL déclenche isolation
#
IDS_RESPONSE_MODE = os.getenv(
    "IDS_RESPONSE_MODE",
    "observe"
).lower()

if IDS_RESPONSE_MODE not in {
    "observe",
    "notify",
    "isolate"
}:
    IDS_RESPONSE_MODE = "observe"


# ============================================================
# LOGGING
# ============================================================

def add_log(
    device,
    severity,
    event_type,
    message,
    resolved=False,
    ip=None
):
    """
    Ajoute un événement au système de logs.
    """

    event = {
        "timestamp": datetime.now().isoformat(),
        "device": str(device),
        "severity": str(severity).upper(),
        "type": str(event_type),
        "message": str(message),
        "resolved": bool(resolved)
    }

    if ip:
        event["ip"] = str(ip)

    with data_lock:

        logs.insert(0, event)

        # Évite que la mémoire grossisse indéfiniment.
        if len(logs) > 1000:
            logs.pop()

    print(
        f"[{event['severity']}] "
        f"{event['device']} | "
        f"{event['type']} | "
        f"{event['message']}"
    )

    return event


# ============================================================
# DEVICE MANAGEMENT
# ============================================================

def register_device(
    device_id,
    ip=None
):
    """
    Enregistre un nouveau device ou met à jour
    les informations d'un device existant.
    """

    now = datetime.now().isoformat()

    with data_lock:

        if device_id not in devices:

            devices[device_id] = {
                "id": device_id,
                "ip": ip or "unknown",
                "status": "ONLINE",
                "last_seen": now
            }

        else:

            if ip:
                devices[device_id]["ip"] = ip

            devices[device_id]["last_seen"] = now

        return devices[device_id]


# ============================================================
# IDS PROCESSING
# ============================================================

def analyze_event(event):
    """
    Envoie un événement à l'IDS.

    Ton AutomaticIDS.process_event() retourne :
        list[dict]

    Exemple :
        [
            {
                "timestamp": "...",
                "device": "VESSEL-01",
                "ip": "10.42.0.100",
                "severity": "CRITICAL",
                "type": "PORT_SCAN",
                "message": "...",
                "resolved": False
            }
        ]
    """

    try:

        alerts = ids.process_event(event)

        if not alerts:
            return []

        return alerts

    except Exception as error:

        print(
            f"❌ Erreur pendant l'analyse IDS : {error}"
        )

        add_log(
            device=event.get(
                "device",
                "SYSTEM"
            ),
            severity="CRITICAL",
            event_type="IDS_ERROR",
            message=(
                f"IDS processing failed: {error}"
            ),
            resolved=False,
            ip=event.get("ip")
        )

        return []


# ============================================================
# SECURITY EVENT PIPELINE
# ============================================================

def process_event(event):
    """
    Pipeline central du système.

    Tous les événements provenant :
        - MQTT
        - /api/alerts
        - éventuellement d'autres sources
    passent par cette fonction.
    """

    # --------------------------------------------------------
    # Validation minimale
    # --------------------------------------------------------

    if not isinstance(event, dict):

        return {
            "success": False,
            "error": "Event must be a JSON object"
        }

    device_id = str(
        event.get(
            "device",
            ""
        )
    ).strip()

    if not device_id:

        return {
            "success": False,
            "error": "Missing device"
        }

    ip = event.get("ip")

    if ip is not None:
        ip = str(ip).strip()

    event_type = str(
        event.get(
            "type",
            event.get(
                "event",
                "UNKNOWN"
            )
        )
    ).upper()

    # --------------------------------------------------------
    # Enrichissement
    # --------------------------------------------------------

    event["device"] = device_id
    event["type"] = event_type

    if ip:
        event["ip"] = ip

    # --------------------------------------------------------
    # Device
    # --------------------------------------------------------

    register_device(
        device_id=device_id,
        ip=ip
    )

    # --------------------------------------------------------
    # IDS
    # --------------------------------------------------------

    alerts = analyze_event(event)

    # --------------------------------------------------------
    # Aucun problème détecté
    # --------------------------------------------------------

    if not alerts:

        # On peut conserver une trace INFO des événements
        # normaux, mais uniquement pour les événements venant
        # explicitement du serveur.
        #
        # Cela évite de remplir inutilement les logs avec
        # chaque événement réseau.

        return {
            "success": True,
            "detected": False,
            "alerts": []
        }

    # --------------------------------------------------------
    # Une ou plusieurs alertes
    # --------------------------------------------------------

    processed_alerts = []

    for alert in alerts:

        alert_device = alert.get(
            "device",
            device_id
        )

        alert_ip = alert.get(
            "ip",
            ip
        )

        severity = str(
            alert.get(
                "severity",
                "WARN"
            )
        ).upper()

        alert_type = alert.get(
            "type",
            "IDS_ALERT"
        )

        message = alert.get(
            "message",
            "Security event detected"
        )

        # ----------------------------------------------------
        # Enregistrement
        # ----------------------------------------------------

        log_event = add_log(
            device=alert_device,
            severity=severity,
            event_type=alert_type,
            message=message,
            resolved=False,
            ip=alert_ip
        )

        # Conserver l'IP dans l'alerte
        alert["ip"] = alert_ip

        # ----------------------------------------------------
        # Réponse automatique
        # ----------------------------------------------------

        if severity == "CRITICAL":

            handle_critical_alert(
                alert=log_event,
                device_id=alert_device,
                device_ip=alert_ip
            )

        processed_alerts.append(
            log_event
        )

    return {
        "success": True,
        "detected": True,
        "alerts": processed_alerts
    }


# ============================================================
# CRITICAL RESPONSE
# ============================================================

def handle_critical_alert(
    alert,
    device_id,
    device_ip
):
    """
    Réponse à une alerte CRITICAL.

    L'IDS détecte.
    Cette fonction décide quoi faire.
    isolation.py effectue réellement le blocage.
    """

    print(
        f"🚨 CRITICAL : "
        f"{device_id} / "
        f"{alert['type']}"
    )

    # --------------------------------------------------------
    # OBSERVE
    # --------------------------------------------------------

    if IDS_RESPONSE_MODE == "observe":

        print(
            "👁️ IDS_RESPONSE_MODE=observe"
            " -> aucune action automatique."
        )

        return

    # --------------------------------------------------------
    # NOTIFY
    # --------------------------------------------------------

    if IDS_RESPONSE_MODE == "notify":

        print(
            "🔔 IDS_RESPONSE_MODE=notify"
            " -> incident enregistré."
        )

        return

    # --------------------------------------------------------
    # ISOLATE
    # --------------------------------------------------------

    if IDS_RESPONSE_MODE == "isolate":

        if handle_alert is None:

            print(
                "❌ Isolation impossible : "
                "isolation.py indisponible."
            )

            add_log(
                device=device_id,
                severity="CRITICAL",
                event_type="ISOLATION_ERROR",
                message=(
                    "Critical alert detected but "
                    "isolation.py is unavailable."
                ),
                resolved=False,
                ip=device_ip
            )

            return

        if not device_ip or device_ip == "unknown":

            print(
                "❌ Isolation impossible : "
                "IP inconnue."
            )

            add_log(
                device=device_id,
                severity="CRITICAL",
                event_type="ISOLATION_ERROR",
                message=(
                    "Critical alert detected but "
                    "device IP is unknown."
                ),
                resolved=False,
                ip=device_ip
            )

            return

        # ----------------------------------------------------
        # Isolation
        # ----------------------------------------------------

        try:

            success = handle_alert(
                alert
            )

        except Exception as error:

            success = False

            print(
                f"❌ Exception isolation : {error}"
            )

        if success:

            with data_lock:

                if device_id in devices:

                    devices[device_id]["status"] = (
                        "ISOLATED"
                    )

            add_log(
                device=device_id,
                severity="CRITICAL",
                event_type="DEVICE_ISOLATED",
                message=(
                    "Device automatically isolated "
                    "after a critical security event."
                ),
                resolved=False,
                ip=device_ip
            )

            print(
                f"🔒 {device_id} ISOLATED"
            )

        else:

            add_log(
                device=device_id,
                severity="CRITICAL",
                event_type="ISOLATION_FAILED",
                message=(
                    "Critical event detected but "
                    "automatic isolation failed."
                ),
                resolved=False,
                ip=device_ip
            )

            print(
                f"❌ Impossible d'isoler {device_id}"
            )


# ============================================================
# MQTT
# ============================================================

def on_mqtt_connect(
    client,
    userdata,
    flags,
    rc
):
    """
    Connexion au broker MQTT.
    """

    if rc != 0:

        print(
            f"❌ Connexion MQTT échouée : {rc}"
        )

        add_log(
            device="SYSTEM",
            severity="CRITICAL",
            event_type="MQTT_CONNECTION_ERROR",
            message=(
                f"MQTT broker connection failed "
                f"with code {rc}"
            ),
            resolved=False
        )

        return

    print(
        "✅ Connecté au broker MQTT."
    )

    print(
        f"📡 Subscription : {MQTT_TOPIC}"
    )

    client.subscribe(
        MQTT_TOPIC,
        qos=1
    )


def on_mqtt_disconnect(
    client,
    userdata,
    rc
):

    print(
        f"⚠️ MQTT déconnecté : {rc}"
    )


def on_mqtt_message(
    client,
    userdata,
    msg
):
    """
    Réception d'un événement MQTT.

    Le payload doit idéalement être du JSON.
    """

    # --------------------------------------------------------
    # Décodage
    # --------------------------------------------------------

    try:
        raw_payload = msg.payload.decode("utf-8")
        
        # CHIFFREMENT MILITAIRE: On tente de déchiffrer !
        decrypted = cypher.decrypt_message(raw_payload)
        
        if decrypted is None:
            # Soit le token est invalide, soit c'est une attaque !
            try:
                event = json.loads(raw_payload)
                add_log("UNKNOWN", "CRITICAL", "UNENCRYPTED_PAYLOAD", "Payload en clair détecté ! Attaque interceptée par le système de chiffrement.", False)
            except:
                add_log("UNKNOWN", "CRITICAL", "INVALID_TOKEN", "Token chiffré invalide ou falsifié intercepté !", False)
            return
            
        event = decrypted.get("data", decrypted)
        print(f"📥 MQTT [Déchiffré] [{msg.topic}]")
        
    except Exception as e:
        add_log("UNKNOWN", "WARN", "MQTT_ERROR", f"MQTT Error: {e}", False)
        return

    if not isinstance(event, dict):

        add_log(
            device="UNKNOWN",
            severity="WARN",
            event_type="MQTT_INVALID_EVENT",
            message=(
                "MQTT payload must contain "
                "a JSON object."
            ),
            resolved=False
        )

        return

    # --------------------------------------------------------
    # Heartbeat
    # --------------------------------------------------------
    #
    # Le heartbeat ne doit pas être envoyé à l'IDS comme
    # une attaque réseau.
    #
    # Il sert principalement à maintenir le statut du device.
    # --------------------------------------------------------

    event_type = str(
        event.get(
            "type",
            ""
        )
    ).upper()

    if event_type == "HEARTBEAT":

        device_id = event.get(
            "device"
        )

        if not device_id:

            add_log(
                device="UNKNOWN",
                severity="WARN",
                event_type="INVALID_HEARTBEAT",
                message=(
                    "Heartbeat without device ID."
                ),
                resolved=False
            )

            return

        now = datetime.now().isoformat()

        register_device(
            device_id=device_id,
            ip=event.get("ip")
        )

        with data_lock:

            if devices[device_id]["status"] != "ISOLATED":

                devices[device_id]["status"] = (
                    "ONLINE"
                )

            devices[device_id]["last_seen"] = now

        print(
            f"💓 Heartbeat : {device_id}"
        )

        return

    # --------------------------------------------------------
    # Tous les autres événements
    # --------------------------------------------------------

    result = process_event(
        event
    )

    if result.get("detected"):

        print(
            f"🚨 {len(result['alerts'])}"
            " alerte(s) générée(s)."
        )


def start_mqtt():

    client = mqtt.Client(
        client_id=MQTT_CLIENT_ID
    )

    client.username_pw_set('v-client', 'secret_iot_2026')
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    client.on_disconnect = on_mqtt_disconnect

    try:

        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        client.loop_start()

        print(
            f"📡 MQTT démarré : "
            f"{MQTT_BROKER}:{MQTT_PORT}"
        )

        return client

    except Exception as error:

        print(
            f"⚠️ Impossible de joindre "
            f"le broker MQTT : {error}"
        )

        add_log(
            device="SYSTEM",
            severity="CRITICAL",
            event_type="MQTT_CONNECTION_ERROR",
            message=str(error),
            resolved=False
        )

        return None


# ============================================================
# WATCHDOG
# ============================================================

def start_watchdog():
    """Run watchdog.py's checks in a background thread, against this
    same server (loopback HTTP), instead of as a separate process."""

    if watchdog_module is None:
        return None

    watchdog_module.SERVER_URL = "http://localhost:5000"

    thread = threading.Thread(
        target=watchdog_module.run_forever,
        name="watchdog",
        daemon=True
    )
    thread.start()

    print(
        "🐕 Watchdog démarré"
        " (vérifie les devices toutes les"
        f" {watchdog_module.CHECK_INTERVAL}s)."
    )

    return thread


# ============================================================
# WEB
# ============================================================

@app.route("/")
def index():

    return send_from_directory(
        WEB_DIR,
        "index.html"
    )


# ============================================================
# API DEVICES
# ============================================================

@app.route(
    "/api/devices",
    methods=["GET"]
)
def api_devices():

    with data_lock:

        return jsonify(
            list(devices.values())
        )


# ============================================================
# API LOGS
# ============================================================

@app.route(
    "/api/logs",
    methods=["GET"]
)
def api_logs():

    with data_lock:
        snapshot = list(logs)

    if sort_by_severity:
        snapshot = sort_by_severity(snapshot)

    return jsonify(snapshot)


# ============================================================
# API ALERTS
# ============================================================

@app.route(
    "/api/alerts",
    methods=["POST"]
)
def receive_alert():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "error": "JSON body required"
        }), 400

    if not isinstance(data, dict):

        return jsonify({
            "error": "JSON object required"
        }), 400

    # --------------------------------------------------------
    # Champs minimum
    # --------------------------------------------------------

    required_fields = [
        "device",
        "type",
        "message"
    ]

    missing = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing:

        return jsonify({
            "error": "Missing fields",
            "fields": missing
        }), 400

    # --------------------------------------------------------
    # Important :
    #
    # Une alerte envoyée à cette route par ids.py est déjà
    # une alerte détectée.
    #
    # On ne repasse donc PAS cette alerte dans l'IDS.
    #
    # Sinon :
    #
    # IDS -> /api/alerts -> IDS -> /api/alerts -> ...
    #
    # pourrait créer une boucle.
    # --------------------------------------------------------

    device_id = str(
        data["device"]
    )

    ip = data.get(
        "ip"
    )

    register_device(
        device_id=device_id,
        ip=ip
    )

    severity_raw = data.get("severity")

    if severity_raw:
        severity = str(severity_raw).upper()
    elif classify_alert:
        # No severity given: classify from the alert's type/message
        # instead of blindly defaulting to WARN.
        severity = classify_alert(data)
    else:
        severity = "WARN"

    event = add_log(
        device=device_id,
        severity=severity,
        event_type=data["type"],
        message=data["message"],
        resolved=data.get(
            "resolved",
            False
        ),
        ip=ip
    )

    # --------------------------------------------------------
    # Réponse automatique
    # --------------------------------------------------------

    if severity == "CRITICAL":

        handle_critical_alert(
            alert=event,
            device_id=device_id,
            device_ip=ip
        )

    return jsonify({
        "success": True,
        "event": event
    }), 201


# ============================================================
# API HEARTBEAT
# ============================================================

@app.route(
    "/api/heartbeat",
    methods=["POST"]
)
def heartbeat():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "error": "JSON body required"
        }), 400

    # ----------------------------------------------------------
    # Heartbeat chiffré (device -> Center Device)
    #
    # Un device peut envoyer {"token": "<fernet>"} au lieu du
    # JSON en clair habituel. Le token vient de
    # cypher.encrypt_message(device_id, {"ip": ...}).
    # Le JSON en clair reste accepté (compatibilité).
    # ----------------------------------------------------------

    if "token" in data:

        if decrypt_heartbeat_token is None:

            return jsonify({
                "error": "Encrypted heartbeats are not supported (cypher.py unavailable)"
            }), 503

        try:
            decrypted = decrypt_heartbeat_token(data["token"])
        except RuntimeError as error:

            return jsonify({
                "error": f"Server misconfiguration: {error}"
            }), 503

        if decrypted is None:

            return jsonify({
                "error": "Invalid, tampered or expired token"
            }), 401

        device_id = str(decrypted.get("device", "")).strip()
        ip = (decrypted.get("data") or {}).get("ip")

        if not device_id:

            return jsonify({
                "error": "Encrypted heartbeat missing device"
            }), 400

    else:

        if "device" not in data:

            return jsonify({
                "error": "device field required"
            }), 400

        device_id = str(
            data["device"]
        )
        ip = data.get("ip")

    now = datetime.now().isoformat()

    register_device(
        device_id=device_id,
        ip=ip
    )

    with data_lock:

        if devices[device_id]["status"] != "ISOLATED":

            devices[device_id]["status"] = "ONLINE"

        devices[device_id]["last_seen"] = now

    return jsonify({
        "success": True,
        "device": device_id,
        "timestamp": now
    })


# ============================================================
# API RESTORE
# ============================================================

@app.route(
    "/api/devices/<device_id>/restore",
    methods=["POST"]
)
def restore_device(device_id):

    # --------------------------------------------------------
    # Device
    # --------------------------------------------------------

    with data_lock:

        device = devices.get(
            device_id
        )

    if device is None:

        return jsonify({
            "error": "Device not found"
        }), 404

    device_ip = device.get(
        "ip"
    )

    if not device_ip or device_ip == "unknown":

        return jsonify({
            "error": "Device has no valid IP"
        }), 400

    # --------------------------------------------------------
    # Isolation module
    # --------------------------------------------------------

    if restore_isolated_device is None:

        return jsonify({
            "error": "isolation.py unavailable"
        }), 503

    # --------------------------------------------------------
    # Restore
    # --------------------------------------------------------

    try:

        success = restore_isolated_device(
            device_ip
        )

    except Exception as error:

        print(
            f"❌ Restore error : {error}"
        )

        return jsonify({
            "error": "Firewall restore failed",
            "details": str(error)
        }), 502

    if not success:

        return jsonify({
            "error": "Firewall restore failed",
            "device": device_id
        }), 502

    # --------------------------------------------------------
    # Update status
    # --------------------------------------------------------

    now = datetime.now().isoformat()

    with data_lock:

        devices[device_id]["status"] = "ONLINE"
        devices[device_id]["last_seen"] = now

    add_log(
        device=device_id,
        severity="INFO",
        event_type="DEVICE_RESTORED",
        message=(
            "Device restored and communication "
            "allowed again."
        ),
        resolved=True,
        ip=device_ip
    )

    return jsonify({
        "success": True,
        "device": device_id,
        "status": "ONLINE"
    })




# ============================================================
# SERVER TELEMETRY THREAD
# ============================================================
import threading
import psutil
import subprocess
import time

def get_wifi_signal():
    try:
        output = subprocess.check_output("iwconfig wlan0 | grep -i quality", shell=True).decode()
        if "Signal level" in output: return output.split("Signal level=")[1].split(" ")[0]
    except: pass
    return "-100"

def server_telemetry_thread():
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
                "wifi_signal": get_wifi_signal(),
                "timestamp": datetime.now().isoformat()
            }
            with data_lock:
                telemetry_data["SERVER"] = payload
        except Exception: pass
        time.sleep(5)

# ============================================================
# API TELEMETRY
# ============================================================


import random
def get_mock_telemetry():
    return {
        "sas-reacteur-01": {
            "cpu_usage": round(random.uniform(12.0, 45.0), 1),
            "ram_usage": round(random.uniform(40.0, 60.0), 1),
            "temp": round(random.uniform(42.0, 58.0), 1),
            "wifi_signal": str(random.randint(-50, -30))
        }
    }

@app.route("/api/telemetry", methods=["GET"])
def get_telemetry():
    if not telemetry_data: return jsonify(get_mock_telemetry())

    with data_lock:
        return jsonify(telemetry_data)

@app.route("/api/telemetry/<device_id>", methods=["POST"])
def post_telemetry(device_id):
    data = request.get_json(silent=True)
    if not data: return jsonify({"error": "JSON body required"}), 400
    with data_lock:
        telemetry_data[device_id] = data
        telemetry_data[device_id]["timestamp"] = datetime.now().isoformat()
    return jsonify({"success": True})

# ============================================================
# API COMMANDS (Red Alert, Lock, Unlock, Scan)
# ============================================================
import paho.mqtt.publish as publish
import json

def send_mqtt_command(topic, payload):
    try:
        publish.single(topic, payload=json.dumps(payload), hostname=MQTT_BROKER, port=MQTT_PORT, auth={'username': 'v-client', 'password': 'secret_iot_2026'})
    except Exception as e:
        print(f"MQTT Command error: {e}")

@app.route("/api/command/lockdown", methods=["POST"])
def lockdown():
    send_mqtt_command("cyberspace/command/global", {"action": "LOCKDOWN"})
    add_log(device="SERVER", severity="CRITICAL", event_type="GLOBAL_LOCKDOWN", message="Alarme rouge déclenchée !", resolved=False, ip="127.0.0.1")
    return jsonify({"success": True})

@app.route("/api/command/door/<device_id>", methods=["POST"])
def door_command(device_id):
    data = request.get_json(silent=True) or {}
    action = data.get("action", "LOCK")
    send_mqtt_command(f"cyberspace/command/{device_id}", {"action": action})
    add_log(device=device_id, severity="WARN", event_type=f"DOOR_{action}", message=f"Commande {action} envoyée au sas", resolved=True, ip="127.0.0.1")
    return jsonify({"success": True})

@app.route("/api/command/scan", methods=["POST"])
def manual_scan():
    add_log(device="SERVER", severity="INFO", event_type="MANUAL_SCAN", message="Scan de sécurité manuel terminé : 0 nouvelle menace.", resolved=True, ip="127.0.0.1")
    return jsonify({"success": True})

# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def api_status():

    with data_lock:

        return jsonify({
            "status": "ONLINE",
            "ids": "ONLINE",
            "mqtt": "ONLINE",
            "response_mode": IDS_RESPONSE_MODE,
            "devices": len(devices),
            "logs": len(logs),
            "timestamp": datetime.now().isoformat()
        })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("       INTER-VESSEL SECURITY CENTER")
    print("=" * 60)
    print()
    print(
        f"🌐 Web           : http://0.0.0.0:5000"
    )
    print(
        f"🛡️ IDS           : AutomaticIDS"
    )
    print(
        f"📡 MQTT Broker   : "
        f"{MQTT_BROKER}:{MQTT_PORT}"
    )
    print(
        f"📨 MQTT Topic    : "
        f"{MQTT_TOPIC}"
    )
    print(
        f"⚙️ Response mode : "
        f"{IDS_RESPONSE_MODE}"
    )
    print()

    # --------------------------------------------------------
    # MQTT
    # --------------------------------------------------------

    mqtt_client = start_mqtt()

    # --------------------------------------------------------
    # Watchdog
    # --------------------------------------------------------

    watchdog_thread = start_watchdog()
    threading.Thread(target=server_telemetry_thread, daemon=True).start()

    # --------------------------------------------------------
    # Flask
    # --------------------------------------------------------

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )
