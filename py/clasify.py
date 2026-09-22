import logging
from datetime import datetime

logger = logging.getLogger("IDS-Classify")

LOG, WARN, CRITICAL = "LOG", "WARN", "CRITICAL"
LEVELS = {LOG: 0, WARN: 1, CRITICAL: 2}

# Risk by alert type (adapt to the types the IDS really emits)
TYPE_SEVERITY = {
    "PORT_SCAN": CRITICAL,
    "BRUTE_FORCE": CRITICAL,
    "MALWARE": CRITICAL,
    "DATA_EXFILTRATION": CRITICAL,
    "UNAUTHORIZED_ACCESS": CRITICAL,
    "AUTH_FAILURE": WARN,
    "HIGH_LATENCY": WARN,
    "PACKET_LOSS": WARN,
    "DEVICE_OFFLINE": WARN,
    "PING": LOG,
    "STATUS": LOG,
}

# Fallback when the type is unknown: look for keywords in the message
KEYWORDS = {
    CRITICAL: ("attack", "intrusion", "malware", "exfiltration", "scan", "unauthorized"),
    WARN: ("timeout", "failed", "latency", "offline", "unstable", "retry"),
}


def classify_alert(alert: dict) -> str:
    """Return LOG, WARN or CRITICAL for an alert."""
    alert_type = str(alert.get("type", "")).upper()
    if alert_type in TYPE_SEVERITY:
        return TYPE_SEVERITY[alert_type]

    message = str(alert.get("message", "")).lower()
    for level in (CRITICAL, WARN):
        if any(word in message for word in KEYWORDS[level]):
            return level

    # Keep the severity already given by the device, if valid
    declared = str(alert.get("severity", "")).upper()
    return declared if declared in LEVELS else LOG


def classify(alert: dict) -> dict:
    """Return a copy of the alert with its 'severity' set."""
    result = dict(alert)
    result["severity"] = classify_alert(alert)
    return result


def sort_alerts(alerts: list[dict]) -> list[dict]:
    """Classify then sort: CRITICAL first, unresolved first, newest first."""
    alerts = [classify(a) for a in alerts]
    return sort_by_severity(alerts)


def sort_by_severity(alerts: list[dict]) -> list[dict]:
    """Sort already-classified alerts: CRITICAL first, unresolved first, newest first.

    Unlike sort_alerts(), this never rewrites an alert's 'severity' - it only
    orders them. Severities outside LOG/WARN/CRITICAL (e.g. "INFO" system
    entries) sort last without being changed.
    """
    # Stable sorts, least important key first
    alerts = sorted(alerts, key=lambda a: a.get("timestamp", ""), reverse=True)
    alerts = sorted(alerts, key=lambda a: bool(a.get("resolved", False)))
    return sorted(
        alerts,
        key=lambda a: LEVELS.get(str(a.get("severity", "")).upper(), -1),
        reverse=True,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    samples = [
        {"timestamp": datetime.now().isoformat(), "device": "VESSEL-01",
         "ip": "192.168.1.10", "type": "PING", "message": "alive", "resolved": True},
        {"timestamp": datetime.now().isoformat(), "device": "VESSEL-02",
         "ip": "192.168.1.20", "type": "HIGH_LATENCY", "message": "slow", "resolved": False},
        {"timestamp": datetime.now().isoformat(), "device": "VESSEL-03",
         "ip": "192.168.1.30", "type": "PORT_SCAN",
         "message": "Abnormal port scanning detected", "resolved": False},
    ]

    for alert in sort_alerts(samples):
        logger.info("%s | %s | %s", alert["severity"], alert["device"], alert["message"])
