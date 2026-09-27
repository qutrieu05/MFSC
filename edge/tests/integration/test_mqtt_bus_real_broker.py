"""Optional smoke test against a real MQTT broker (MT-02..05 groundwork).

Skips itself (reported honestly as SKIPPED, never as PASS) when no broker answers on
127.0.0.1:1883 within a short timeout — Mosquitto is blocker B4 in docs/PHASE1_PLAN.md and
is not yet installed as of Phase 1 P1.7. Once it is, this test starts exercising the real
network path (TCP connect, CONNACK, publish/subscribe round trip) without any fake client.
"""

from __future__ import annotations

import json
import socket
import time

import pytest

from msfc.comm import MqttBus

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
PROBE_TIMEOUT_S = 0.3


def _broker_reachable() -> bool:
    try:
        with socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=PROBE_TIMEOUT_S):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _broker_reachable(),
    reason=f"no MQTT broker reachable at {BROKER_HOST}:{BROKER_PORT} (install Mosquitto — blocker B4)",
)


def test_publish_subscribe_round_trip_over_a_real_broker() -> None:
    received: list[tuple[str, dict]] = []
    subscriber = MqttBus(host=BROKER_HOST, port=BROKER_PORT, client_id="msfc-test-sub")
    subscriber.subscribe("msfc/test/+", lambda t, e: received.append((t, e)))
    subscriber.start()

    publisher = MqttBus(host=BROKER_HOST, port=BROKER_PORT, client_id="msfc-test-pub")
    publisher.start()
    try:
        publisher.publish("msfc/test/ping", {"schema": "test.v1", "device_id": "test01",
                                              "seq": 0, "mono_ms": 0, "data": {"ok": True}}, qos=1)

        deadline = time.monotonic() + 2.0
        while not received and time.monotonic() < deadline:
            time.sleep(0.05)
    finally:
        publisher.stop()
        subscriber.stop()

    assert received, "expected the round-tripped message to arrive within 2s"
    topic, envelope = received[0]
    assert topic == "msfc/test/ping"
    assert envelope["data"] == {"ok": True}
