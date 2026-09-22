"""Small event-driven IDS for the IoT workshop.

The detector consumes JSON events, emits alerts, and optionally sends them to
server.py. It deliberately performs no blocking, isolation, or remediation.

Example event formats:
    {"device": "VESSEL-01", "ip": "192.168.1.10",
     "type": "AUTH_FAILURE", "username": "admin"}
    {"device": "VESSEL-01", "ip": "192.168.1.10",
     "type": "CONNECTION", "destination_port": 23, "success": false}
    {"device": "VESSEL-01", "ip": "192.168.1.10",
     "type": "COMMAND", "payload": "../../etc/passwd"}

Run with JSON lines from stdin:
    python py/ids.py --device VESSEL-01 --server-url http://localhost:5000

Or monitor a file continuously:
    python py/ids.py --input-file events.jsonl --follow --device VESSEL-01
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("IDS-Detect")

CRITICAL = "CRITICAL"
WARN = "WARN"

SUSPICIOUS_PAYLOAD = re.compile(
    r"(?:\.\./|%2e%2e|union\s+select|<\s*script|/bin/(?:sh|bash)|"
    r"cmd(?:\.exe)?\s*/c|powershell(?:\.exe)?|wget\s+https?://|curl\s+https?://)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DetectorConfig:
    auth_failure_threshold: int = 5
    auth_window_seconds: int = 60
    port_scan_threshold: int = 10
    port_scan_window_seconds: int = 30
    alert_cooldown_seconds: int = 60


class AutomaticIDS:
    """Detect a few high-signal attack patterns in normalized event dictionaries."""

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()
        self._auth_failures: defaultdict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._scanned_ports: defaultdict[str, deque[tuple[float, int]]] = defaultdict(deque)
        self._last_alert: dict[tuple[str, str], float] = {}

    def process_event(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Return alerts for one event without taking any countermeasure."""
        device = str(event.get("device", "")).strip()
        source_ip = str(event.get("ip", event.get("source_ip", ""))).strip()
        if not device or not source_ip:
            logger.warning("Ignoring event without device and source IP: %s", event)
            return []

        now = _event_time(event)
        event_type = str(event.get("type", event.get("event", ""))).upper()
        alerts: list[dict[str, Any]] = []

        if event_type in {"AUTH_FAILURE", "AUTH_FAILED", "LOGIN_FAILURE"}:
            alerts.extend(self._check_brute_force(device, source_ip, event, now))

        if event_type in {"CONNECTION", "NETWORK_CONNECTION", "PORT_PROBE", "PORT_SCAN"}:
            alerts.extend(self._check_port_scan(device, source_ip, event, now))

        payload = " ".join(
            str(event.get(field, ""))
            for field in ("payload", "message", "command", "path")
        )
        if SUSPICIOUS_PAYLOAD.search(payload):
            alert = self._alert(
                device=device,
                source_ip=source_ip,
                alert_type="SUSPICIOUS_PAYLOAD",
                severity=WARN,
                message="Suspicious command or payload pattern detected",
                now=now,
            )
            if alert:
                alerts.append(alert)

        return alerts

    def _check_brute_force(
        self,
        device: str,
        source_ip: str,
        event: dict[str, Any],
        now: float,
    ) -> list[dict[str, Any]]:
        username = str(event.get("username", "unknown")).strip() or "unknown"
        key = (source_ip, username)
        failures = self._auth_failures[key]
        failures.append(now)
        _discard_before(failures, now - self.config.auth_window_seconds)
        if len(failures) < self.config.auth_failure_threshold:
            return []

        alert = self._alert(
            device=device,
            source_ip=source_ip,
            alert_type="BRUTE_FORCE",
            severity=CRITICAL,
            message=(
                f"{len(failures)} authentication failures for {username} "
                f"within {self.config.auth_window_seconds}s"
            ),
            now=now,
        )
        return [alert] if alert else []

    def _check_port_scan(
        self,
        device: str,
        source_ip: str,
        event: dict[str, Any],
        now: float,
    ) -> list[dict[str, Any]]:
        try:
            port = int(event.get("destination_port", event.get("port")))
        except (TypeError, ValueError):
            return []
        if not 1 <= port <= 65535:
            return []

        probes = self._scanned_ports[source_ip]
        probes.append((now, port))
        _discard_before(probes, now - self.config.port_scan_window_seconds)
        distinct_ports = {seen_port for _, seen_port in probes}
        if len(distinct_ports) < self.config.port_scan_threshold:
            return []

        alert = self._alert(
            device=device,
            source_ip=source_ip,
            alert_type="PORT_SCAN",
            severity=CRITICAL,
            message=(
                f"Probes against {len(distinct_ports)} ports from {source_ip} "
                f"within {self.config.port_scan_window_seconds}s"
            ),
            now=now,
        )
        return [alert] if alert else []

    def _alert(
        self,
        device: str,
        source_ip: str,
        alert_type: str,
        severity: str,
        message: str,
        now: float,
    ) -> dict[str, Any] | None:
        cooldown_key = (source_ip, alert_type)
        previous = self._last_alert.get(cooldown_key)
        if previous is not None and now - previous < self.config.alert_cooldown_seconds:
            return None
        self._last_alert[cooldown_key] = now
        return {
            "timestamp": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "device": device,
            "ip": source_ip,
            "severity": severity,
            "type": alert_type,
            "message": message,
            "resolved": False,
        }


class AlertSender:
    """POST detector alerts to the existing Flask API."""

    def __init__(self, server_url: str, timeout_seconds: float = 5.0) -> None:
        self.endpoint = server_url.rstrip("/") + "/api/alerts"
        self.timeout_seconds = timeout_seconds

    def send(self, alert: dict[str, Any]) -> bool:
        body = json.dumps(alert).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if 200 <= response.status < 300:
                    return True
                logger.error("Server rejected alert with HTTP %s", response.status)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            logger.error("Could not send alert to %s: %s", self.endpoint, error)
        return False


def _event_time(event: dict[str, Any]) -> float:
    value = event.get("timestamp")
    if not value:
        return time.time()
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        logger.warning("Invalid event timestamp %r; using current time", value)
        return time.time()


def _discard_before(values: deque[Any], cutoff: float) -> None:
    while values:
        first = values[0]
        first_time = first if isinstance(first, (int, float)) else first[0]
        if first_time >= cutoff:
            break
        values.popleft()


def read_events(stream: Any, follow: bool = False) -> Iterator[dict[str, Any]]:
    while True:
        line = stream.readline()
        if not line:
            if not follow:
                return
            time.sleep(1)
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            logger.warning("Ignoring malformed JSON event: %s", error)
            continue
        if isinstance(event, dict):
            yield event


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the workshop event-driven IDS")
    parser.add_argument("--server-url", default="http://localhost:5000")
    parser.add_argument("--device", help="Default device for events missing a device")
    parser.add_argument("--input-file", help="Read JSON events from this file instead of stdin")
    parser.add_argument("--follow", action="store_true", help="Wait for new lines in --input-file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    detector = AutomaticIDS()
    sender = AlertSender(args.server_url)
    input_stream = open(args.input_file, "r", encoding="utf-8") if args.input_file else sys.stdin
    try:
        for event in read_events(input_stream, follow=args.follow):
            if args.device and not event.get("device"):
                event["device"] = args.device
            for alert in detector.process_event(event):
                logger.warning("Detected %s: %s", alert["type"], alert["message"])
                sender.send(alert)
    finally:
        if args.input_file:
            input_stream.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
