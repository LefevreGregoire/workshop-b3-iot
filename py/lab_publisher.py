"""Publish safe synthetic IDS events for a private Raspberry Pi lab."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import paho.mqtt.publish as publish


def event(device: str, ip: str, event_type: str, **fields: object) -> dict[str, object]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "ip": ip,
        "type": event_type,
        **fields,
    }


def publish_event(broker: str, topic: str, payload: dict[str, object]) -> None:
    publish.single(
        topic,
        payload=json.dumps(payload),
        hostname=broker,
        port=1883,
        qos=1,
    )
    print(f"published {payload['type']} for {payload['device']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish safe IDS test events")
    parser.add_argument("--broker", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--ip", required=True)
    parser.add_argument(
        "--scenario",
        choices=("brute-force", "port-scan", "payload", "heartbeat"),
        required=True,
    )
    args = parser.parse_args()
    topic = f"ids/devices/{args.device}/events"

    if args.scenario == "brute-force":
        for _ in range(5):
            publish_event(
                args.broker,
                topic,
                event(args.device, args.ip, "AUTH_FAILURE", username="lab-user"),
            )
            time.sleep(0.2)
    elif args.scenario == "port-scan":
        for port in range(1, 11):
            publish_event(
                args.broker,
                topic,
                event(args.device, args.ip, "CONNECTION", destination_port=port),
            )
            time.sleep(0.2)
    elif args.scenario == "payload":
        publish_event(
            args.broker,
            topic,
            event(args.device, args.ip, "COMMAND", payload="../../etc/passwd"),
        )
    else:
        publish_event(args.broker, topic, event(args.device, args.ip, "HEARTBEAT"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
