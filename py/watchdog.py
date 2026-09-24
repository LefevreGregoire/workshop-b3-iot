import logging
import time
from datetime import datetime

import requests

logger = logging.getLogger("IDS-Watchdog")

SERVER_URL = "http://localhost:5000"
CHECK_INTERVAL = 30       # seconds between checks
OFFLINE_THRESHOLD = 60    # seconds without heartbeat before a device is flagged offline

# Devices already reported offline, so we don't spam an alert every 30s
_flagged_offline = set()


def get_devices() -> list[dict]:
    response = requests.get(f"{SERVER_URL}/api/devices", timeout=5)
    response.raise_for_status()
    return response.json()


def get_logs() -> list[dict]:
    response = requests.get(f"{SERVER_URL}/api/logs", timeout=5)
    response.raise_for_status()
    return response.json()


def send_alert(device: str, severity: str, event_type: str, message: str) -> None:
    requests.post(
        f"{SERVER_URL}/api/alerts",
        json={
            "device": device,
            "severity": severity,
            "type": event_type,
            "message": message,
        },
        timeout=5,
    )


def check_offline_devices() -> None:
    """Flag devices that stopped sending heartbeats."""
    for device in get_devices():
        device_id = device["id"]
        last_seen = device.get("last_seen")

        if device["status"] == "ISOLATED":
            continue

        if not last_seen:
            # Never sent a heartbeat yet, nothing to compare against
            continue

        try:
            last_seen_dt = datetime.fromisoformat(last_seen)
        except ValueError:
            # Not a real timestamp (e.g. a display placeholder like "Jamais")
            continue

        elapsed = (datetime.now() - last_seen_dt).total_seconds()

        if elapsed > OFFLINE_THRESHOLD:
            if device_id not in _flagged_offline:
                logger.warning(
                    "Device %s offline (no heartbeat for %.0fs)",
                    device_id, elapsed
                )
                send_alert(
                    device=device_id,
                    severity="WARN",
                    event_type="DEVICE_OFFLINE",
                    message=f"No heartbeat for {elapsed:.0f}s.",
                )
                _flagged_offline.add(device_id)
        else:
            _flagged_offline.discard(device_id)


def check_unresolved_problems() -> None:
    """Remind about CRITICAL alerts that are still not resolved."""
    unresolved = [
        log for log in get_logs()
        if log.get("severity") == "CRITICAL" and not log.get("resolved", False)
    ]

    if unresolved:
        logger.critical(
            "%d unresolved CRITICAL alert(s): %s",
            len(unresolved),
            ", ".join(f"{log['device']} ({log['type']})" for log in unresolved),
        )


def run_once() -> None:
    check_offline_devices()
    check_unresolved_problems()


def run_forever(interval: int = CHECK_INTERVAL) -> None:
    logger.info("Watchdog started (checking every %ss).", interval)
    while True:
        try:
            run_once()
        except requests.RequestException as error:
            logger.error("Could not reach the server: %s", error)
        except Exception as error:
            # Never let one bad iteration kill the watchdog thread for good.
            logger.error("Unexpected error during a check: %s", error)
        time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
