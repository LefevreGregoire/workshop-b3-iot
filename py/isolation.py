import logging
import subprocess
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_FILE = Path("response.log")

# Set to False while developing/testing.
# Set to True when the firewall implementation is ready.
FIREWALL_ENABLED = False


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("IDS-Response")


# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------

isolated_devices = set()


# ---------------------------------------------------------------------------
# Firewall
# ---------------------------------------------------------------------------

def execute_firewall_command(command: list[str]) -> bool:
    """
    Execute a firewall command.

    This function is the only place that should directly modify
    the system firewall.
    """

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

    except subprocess.CalledProcessError as error:
        logger.error(
            "Firewall command failed: %s",
            error.stderr.strip()
        )
        return False


def isolate_device(device_ip: str) -> bool:
    """
    Isolate a device from the network.

    Replace the example firewall command with the firewall
    technology used by the Raspberry Pi infrastructure.
    """

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

    # Example nftables command.
    #
    # IMPORTANT:
    # Adapt this to your actual network architecture before
    # enabling FIREWALL_ENABLED.
    command = [
        "nft",
        "add",
        "rule",
        "inet",
        "filter",
        "forward",
        "ip",
        "saddr",
        device_ip,
        "drop"
    ]

    if execute_firewall_command(command):
        isolated_devices.add(device_ip)

        logger.critical(
            "Device %s successfully isolated.",
            device_ip
        )

        return True

    return False


def restore_device(device_ip: str) -> bool:
    """
    Restore a previously isolated device.

    The exact firewall deletion command depends on the
    final firewall architecture.
    """

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

    # The exact command should be implemented once the
    # final firewall rule management strategy is defined.

    isolated_devices.remove(device_ip)

    logger.info(
        "Device %s restored.",
        device_ip
    )

    return True


# ---------------------------------------------------------------------------
# Alert processing
# ---------------------------------------------------------------------------

def handle_alert(alert: dict) -> bool:
    """
    Process an IDS alert.

    Expected format:

    {
        "timestamp": "2026-09-21T14:32:08",
        "device": "VESSEL-03",
        "ip": "192.168.1.30",
        "severity": "CRITICAL",
        "type": "PORT_SCAN",
        "message": "Abnormal port scanning detected",
        "resolved": false
    }
    """

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

    device = alert["device"]
    severity = alert["severity"].upper()

    logger.info(
        "Alert received | device=%s | severity=%s",
        device,
        severity
    )

    if severity != "CRITICAL":
        logger.info(
            "No automatic isolation required for %s.",
            device
        )
        return True

    device_ip = alert.get("ip")

    if not device_ip:
        logger.error(
            "Cannot isolate %s: no IP address provided.",
            device
        )
        return False

    return isolate_device(device_ip)


# ---------------------------------------------------------------------------
# Manual test
# ---------------------------------------------------------------------------

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

