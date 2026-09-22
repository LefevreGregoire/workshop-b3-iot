import logging
import ipaddress
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(os.getenv("IDS_ACTIONS_LOG", "response.log"))
STATE_FILE = Path(os.getenv("IDS_ISOLATION_STATE", "isolated_devices.json"))
FIREWALL_ENABLED = os.getenv("IDS_DRY_RUN", "1").lower() not in {"1", "true", "yes", "on"}
FIREWALL_COMMAND = os.getenv("IDS_FIREWALL_COMMAND", "iptables")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IDS-Response")


def normalize_ip(device_ip: str) -> str:
    """Validate and normalize an IPv4 or IPv6 address."""
    return str(ipaddress.ip_address(str(device_ip).strip()))


def _load_isolated_devices() -> set[str]:
    try:
        values = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(values, list):
            raise ValueError("state must be a JSON list")
        return {normalize_ip(value) for value in values}
    except FileNotFoundError:
        return set()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        logger.error("Could not load isolation state from %s: %s", STATE_FILE, error)
        return set()


def _save_isolated_devices() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = STATE_FILE.with_suffix(f"{STATE_FILE.suffix}.tmp")
    temporary_file.write_text(
        json.dumps(sorted(isolated_devices), indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_file.replace(STATE_FILE)


isolated_devices = _load_isolated_devices()


def is_isolated(device_ip: str) -> bool:
    try:
        return normalize_ip(device_ip) in isolated_devices
    except ValueError:
        return False

def execute_firewall_command(command: list[str]) -> bool:
    if not FIREWALL_ENABLED:
        logger.warning(
            "Firewall disabled - simulated command: %s",
            " ".join(command)
        )
        return True

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(
            "Firewall command executed: %s",
            " ".join(command)
        )

        return True

    except (OSError, subprocess.CalledProcessError) as error:
        logger.error(
            "Firewall command failed: %s",
            getattr(error, "stderr", None) or str(error),
        )
        return False


def isolate_device(device_ip: str) -> bool:
    try:
        device_ip = normalize_ip(device_ip)
    except ValueError:
        logger.error("Cannot isolate invalid IP address %r.", device_ip)
        return False

    if device_ip in isolated_devices:
        logger.warning(
            "Device %s is already isolated.",
            device_ip
        )
        return True

    logger.critical(
        "ISOLATING DEVICE %s",
        device_ip
    )
    command = [
        FIREWALL_COMMAND,
        "-I",
        "FORWARD",
        "-s",
        device_ip,
        "-j",
        "DROP",
    ]

    if execute_firewall_command(command):
        isolated_devices.add(device_ip)
        try:
            _save_isolated_devices()
        except OSError as error:
            isolated_devices.remove(device_ip)
            logger.error("Could not persist isolation state: %s", error)
            return False

        logger.critical(
            "Device %s successfully isolated.",
            device_ip
        )

        return True

    return False


def restore_device(device_ip: str) -> bool:
    try:
        device_ip = normalize_ip(device_ip)
    except ValueError:
        logger.error("Cannot restore invalid IP address %r.", device_ip)
        return False

    if device_ip not in isolated_devices:
        logger.warning(
            "Device %s is not currently isolated.",
            device_ip
        )
        return True

    logger.info(
        "Restoring device %s...",
        device_ip
    )
    command = [
        FIREWALL_COMMAND,
        "-D",
        "FORWARD",
        "-s",
        device_ip,
        "-j",
        "DROP",
    ]
    if not execute_firewall_command(command):
        return False

    isolated_devices.remove(device_ip)
    try:
        _save_isolated_devices()
    except OSError as error:
        logger.error("Could not persist restored state: %s", error)
        return False
    logger.info(
        "Device %s restored.",
        device_ip
    )
    return True

def handle_alert(alert: dict) -> bool:
    required_fields = [
        "device",
        "severity"
    ]

    for field in required_fields:
        if field not in alert:
            logger.error(
                "Invalid alert: missing '%s'",
                field
            )
            return False

    device = str(alert["device"]).strip()
    severity = str(alert["severity"]).upper()

    if not device or severity not in {"LOG", "WARN", "CRITICAL"}:
        logger.error("Invalid alert identity or severity: %s", alert)
        return False

    logger.info(
        "Alert received | device=%s | severity=%s",
        device,
        severity
    )

    device_ip = alert.get("ip")

    if alert.get("resolved") and device_ip:
        return restore_device(device_ip)

    if severity != "CRITICAL":
        logger.info(
            "No automatic isolation required for %s.",
            device
        )
        return True

    if not device_ip:
        logger.error(
            "Cannot isolate %s: no IP address provided.",
            device
        )
        return False

    return isolate_device(device_ip)

if __name__ == "__main__":

    test_alert = {
        "timestamp": datetime.now().isoformat(),
        "device": "VESSEL-03",
        "ip": "192.168.1.30",
        "severity": "CRITICAL",
        "type": "PORT_SCAN",
        "message": "Abnormal port scanning detected",
        "resolved": False
    }

    handle_alert(test_alert)

