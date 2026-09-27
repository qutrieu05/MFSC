"""Tests for msfc.comm.mqtt_bus.MqttBus, driven entirely by a FakeMqttClient test double.

No real broker is required or contacted here — that is exactly the point of injecting
``client_factory`` (see mqtt_bus.py's module docstring). A broker-required smoke test lives
in edge/tests/integration/test_mqtt_bus_real_broker.py and skips itself when Mosquitto
(blocker B4) is not installed.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from msfc.core.errors import ContractError
from msfc.comm import MqttBus, ReconnectBackoff


class FakeMqttClient:
    """Stands in for paho.mqtt.client.Client; implements just what MqttBus calls."""

    def __init__(self) -> None:
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None
        self.username: str | None = None
        self.password: str | None = None
        self.will: tuple | None = None
        self.connect_calls: list[tuple] = []
        self.publish_calls: list[tuple] = []
        self.subscribe_calls: list[tuple] = []
        self.loop_started = False
        self.disconnected = False
        self._fail_times = 0

    def fail_connect_times(self, n: int) -> None:
        self._fail_times = n

    def username_pw_set(self, username, password=None) -> None:
        self.username, self.password = username, password

    def will_set(self, topic, payload, qos, retain) -> None:
        self.will = (topic, payload, qos, retain)

    def connect(self, host, port, keepalive) -> None:
        self.connect_calls.append((host, port, keepalive))
        if self._fail_times > 0:
            self._fail_times -= 1
            raise OSError("connection refused (fake)")
        if self.on_connect:
            self.on_connect(self, None, {}, 0)

    def disconnect(self) -> None:
        self.disconnected = True
        if self.on_disconnect:
            self.on_disconnect(self, None, 0)

    def loop_start(self) -> None:
        self.loop_started = True

    def loop_stop(self) -> None:
        self.loop_started = False

    def publish(self, topic, payload, qos, retain) -> None:
        self.publish_calls.append((topic, payload, qos, retain))

    def subscribe(self, topic, qos) -> None:
        self.subscribe_calls.append((topic, qos))

    def deliver(self, topic: str, payload: bytes) -> None:
        """Test helper: simulate an incoming PUBLISH from the broker."""
        if self.on_message:
            self.on_message(self, None, SimpleNamespace(topic=topic, payload=payload))


@pytest.fixture()
def fake() -> FakeMqttClient:
    return FakeMqttClient()


def make_bus(fake: FakeMqttClient, **kwargs) -> MqttBus:
    return MqttBus(host="127.0.0.1", port=1883, client_id="edge01",
                    client_factory=lambda client_id: fake, **kwargs)


# --------------------------------------------------------------------------- connect / lifecycle
def test_start_connects_and_starts_the_network_loop(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    bus.start()
    assert fake.connect_calls == [("127.0.0.1", 1883, 15)]
    assert fake.loop_started is True
    assert bus.is_connected is True


def test_stop_stops_loop_and_disconnects(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    bus.start()
    bus.stop()
    assert fake.loop_started is False
    assert fake.disconnected is True
    assert bus.is_connected is False


def test_username_and_password_are_forwarded(fake: FakeMqttClient) -> None:
    make_bus(fake, username="edge_server", password="secret")
    assert fake.username == "edge_server" and fake.password == "secret"


def test_no_username_skips_username_pw_set(fake: FakeMqttClient) -> None:
    make_bus(fake)
    assert fake.username is None


# --------------------------------------------------------------------------- publish
def test_publish_json_encodes_the_envelope(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    bus.publish("factory/line01/system/edge01/heartbeat", {"data": {"uptime_ms": 1}}, qos=1, retain=True)
    assert fake.publish_calls == [
        ("factory/line01/system/edge01/heartbeat",
         json.dumps({"data": {"uptime_ms": 1}}).encode("utf-8"), 1, True)
    ]


# --------------------------------------------------------------------------- subscribe
def test_subscribe_before_start_is_applied_on_connect(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    bus.subscribe("factory/line01/conveyor/+/status", lambda t, e: None)
    assert fake.subscribe_calls == []  # not yet connected
    bus.start()
    assert fake.subscribe_calls == [("factory/line01/conveyor/+/status", 1)]


def test_subscribe_after_start_is_applied_immediately(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    bus.start()
    bus.subscribe("factory/line01/conveyor/+/state", lambda t, e: None)
    assert fake.subscribe_calls == [("factory/line01/conveyor/+/state", 1)]


# --------------------------------------------------------------------------- incoming messages
def test_on_message_dispatches_decoded_envelope_to_matching_handler(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    received = []
    bus.subscribe("factory/line01/conveyor/+/status", lambda t, e: received.append((t, e)))
    bus.start()

    fake.deliver("factory/line01/conveyor/esp32-cc01/status",
                  json.dumps({"data": {"online": True}}).encode("utf-8"))

    assert received == [("factory/line01/conveyor/esp32-cc01/status", {"data": {"online": True}})]


def test_on_message_ignores_non_matching_topic(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    received = []
    bus.subscribe("factory/line01/conveyor/+/status", lambda t, e: received.append(e))
    bus.start()

    fake.deliver("factory/line01/vision/cam01/status", json.dumps({"data": {}}).encode("utf-8"))

    assert received == []


def test_on_message_drops_malformed_json_without_raising(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    bus.subscribe("t", lambda t, e: None)
    bus.start()
    fake.deliver("t", b"{not valid json")  # must not raise


def test_on_message_handler_exception_is_caught_and_does_not_propagate(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)

    def boom(topic, envelope):
        raise RuntimeError("handler bug")

    bus.subscribe("t", boom)
    bus.start()
    fake.deliver("t", json.dumps({"data": {}}).encode("utf-8"))  # must not raise


# --------------------------------------------------------------------------- reconnect backoff
def test_transient_connect_failures_are_retried_with_backoff(fake: FakeMqttClient) -> None:
    fake.fail_connect_times(2)
    sleeps: list[float] = []
    bus = make_bus(fake, backoff=ReconnectBackoff(base_s=0.01, factor=2.0, max_s=1.0),
                    sleep=sleeps.append)

    bus.start()

    assert len(fake.connect_calls) == 3  # 2 failures + 1 success
    assert sleeps == [0.01, 0.02]
    assert bus.is_connected is True


def test_max_connect_attempts_exhausted_raises(fake: FakeMqttClient) -> None:
    fake.fail_connect_times(10)
    bus = make_bus(fake, max_connect_attempts=2,
                    backoff=ReconnectBackoff(base_s=0.001, factor=2.0, max_s=0.01),
                    sleep=lambda s: None)

    with pytest.raises(OSError):
        bus.start()
    assert len(fake.connect_calls) == 2


# --------------------------------------------------------------------------- Last Will
def test_set_will_before_start_encodes_payload(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    bus.set_will("factory/line01/system/edge01/status", {"data": {"online": False}}, qos=1, retain=True)
    assert fake.will == (
        "factory/line01/system/edge01/status",
        json.dumps({"data": {"online": False}}).encode("utf-8"),
        1, True,
    )


def test_set_will_after_start_is_rejected(fake: FakeMqttClient) -> None:
    bus = make_bus(fake)
    bus.start()
    with pytest.raises(ContractError, match="before start"):
        bus.set_will("t", {"data": {}})
