from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import os
from pathlib import Path

try:
    from .isolation import handle_alert, is_isolated, restore_device as restore_isolated_device
except ImportError:
    from isolation import handle_alert, is_isolated, restore_device as restore_isolated_device

app = Flask(
    __name__,
    static_folder="../web",
    static_url_path=""
)

devices = {}
logs = []

def add_log(
    device,
    severity,
    event_type,
    message,
    resolved=False
):
    event = {
        "timestamp": datetime.now().isoformat(),
        "device": device,
        "severity": severity,
        "type": event_type,
        "message": message,
        "resolved": resolved
    }
    logs.append(event)
    return event

@app.route("/")
def index():
    return send_from_directory("../web", "index.html")

@app.route("/api/devices", methods=["GET"])
def get_devices():
    return jsonify(
        list(devices.values())
    )

@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify(logs)

@app.route("/api/alerts", methods=["POST"])
def receive_alert():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON body required"
        }), 400


    required_fields = [
        "device",
        "severity",
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

    device_id = data["device"]
    if device_id not in devices:

        devices[device_id] = {
            "id": device_id,
            "ip": data.get("ip", "unknown"),
            "status": "ONLINE",
            "last_seen": None
        }

    event = add_log(
        device=device_id,
        severity=str(data["severity"]).upper(),
        event_type=data["type"],
        message=data["message"],
        resolved=data.get("resolved", False)
    )

    event["ip"] = data.get("ip", devices[device_id].get("ip"))
    response_mode = os.getenv("IDS_RESPONSE_MODE", "observe").lower()
    if response_mode not in {"observe", "notify", "isolate"}:
        response_mode = "observe"

    if response_mode == "isolate" and not handle_alert(event):
        return jsonify({
            "error": "Isolation action failed",
            "event": event
        }), 502

    if response_mode == "isolate" and event["severity"] == "CRITICAL" and not event["resolved"]:
        devices[device_id]["status"] = "ISOLATED"
    elif event["resolved"] and event["ip"] and not is_isolated(event["ip"]):
        devices[device_id]["status"] = "ONLINE"


    return jsonify({
        "success": True,
        "event": event
    }), 201

@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():

    data = request.get_json()

    if not data or "device" not in data:
        return jsonify({
            "error": "device field required"
        }), 400

    device_id = data["device"]
    now = datetime.now().isoformat()

    if device_id not in devices:
        devices[device_id] = {
            "id": device_id,
            "ip": data.get("ip", "unknown"),
            "status": "ONLINE",
            "last_seen": now
        }

    else:
        devices[device_id]["last_seen"] = now
        if devices[device_id]["status"] != "ISOLATED":
            devices[device_id]["status"] = "ONLINE"

    return jsonify({
        "success": True,
        "device": device_id,
        "timestamp": now
    })

@app.route("/api/devices/<device_id>/restore", methods=["POST"])
def restore_device(device_id):

    if device_id not in devices:
        return jsonify({
            "error": "Device not found"
        }), 404


    device_ip = devices[device_id].get("ip")
    if not device_ip or not restore_isolated_device(device_ip):
        return jsonify({
            "error": "Firewall restore failed",
            "device": device_id
        }), 502

    devices[device_id]["status"] = "ONLINE"


    add_log(
        device=device_id,
        severity="INFO",
        event_type="DEVICE_RESTORED",
        message="Device restored and communication allowed again.",
        resolved=True
    )


    return jsonify({
        "success": True,
        "device": device_id,
        "status": "ONLINE"
    })

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )