"""MessageBus backed by a real MQTT broker (paho-mqtt), for Phase 1 once Mosquitto is
installed (blocker B4 in docs/PHASE1_PLAN.md — not yet resolved as of this writing).

Design notes:

* This class does **not** validate envelopes against their schema — that is
  :class:`msfc.contracts.PayloadValidator`'s job. Keeping the two separate means the bus
  works the same whether the caller is strict (validates every message) or permissive
  (a diagnostic tool that just wants to see raw traffic).
* Only malformed JSON is handled here (dropped + logged), because that is a transport-level
  concern this class owns; a well-formed-but-schema-invalid payload is the caller's problem.
* The *initial* ``connect()`` call is retried with :class:`~msfc.comm.backoff.ReconnectBackoff`
  because paho's ``connect()`` raises synchronously on failure and does not retry itself.
  Once ``loop_start()`` is running, paho's own ``reconnect_on_failure`` (enabled by default)
  keeps the connection alive after that — this class does not duplicate that logic.
* The concrete client is injected via ``client_factory`` so unit tests run against a
  ``FakeMqttClient`` instead of a real socket (see edge/tests/unit/test_comm_mqtt_bus.py).
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, Callable, Protocol

from msfc.comm.backoff import ReconnectBackoff
from msfc.comm.bus import Handler
from msfc.comm.topic_match import compile_topic_filter
from msfc.core.errors import ContractError
from msfc.core.logging_setup import ctx, get_logger

log = get_logger("msfc.comm.mqtt")


class MqttClientLike(Protocol):
    """The subset of ``paho.mqtt.client.Client`` this module depends on.

    Any object with this shape can be handed to :class:`MqttBus` via ``client_factory`` —
    real paho client for production, ``FakeMqttClient`` for tests.
    """

    on_connect: Callable[..., None] | None
    on_disconnect: Callable[..., None] | None
    on_message: Callable[..., None] | None

    def username_pw_set(self, username: str, password: str | None = None) -> None: ...
    def will_set(self, topic: str, payload: bytes, qos: int, retain: bool) -> None: ...
    def connect(self, host: str, port: int, keepalive: int) -> Any: ...
    def disconnect(self) -> Any: ...
    def loop_start(self) -> Any: ...
    def loop_stop(self) -> Any: ...
    def publish(self, topic: str, payload: bytes, qos: int, retain: bool) -> Any: ...
    def subscribe(self, topic: str, qos: int) -> Any: ...


def _default_client_factory(client_id: str) -> MqttClientLike:
    import paho.mqtt.client as mqtt  # imported lazily: not needed at all when tests inject a fake

    return mqtt.Client(client_id=client_id)


class MqttBus:
    """:class:`~msfc.comm.bus.MessageBus` implementation over paho-mqtt."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        client_id: str,
        username: str = "",
        password: str = "",
        keepalive_s: int = 15,
        backoff: ReconnectBackoff | None = None,
        max_connect_attempts: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
        client_factory: Callable[[str], MqttClientLike] = _default_client_factory,
    ) -> None:
        self._host = host
        self._port = port
        self._keepalive_s = keepalive_s
        self._backoff = backoff or ReconnectBackoff()
        self._max_attempts = max_connect_attempts
        self._sleep = sleep
        self._client = client_factory(client_id)
        if username:
            self._client.username_pw_set(username, password or None)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._subs: list[tuple[str, re.Pattern[str], Handler]] = []
        self._connected = threading.Event()

    # ------------------------------------------------------------------ lifecycle
    def set_will(self, topic: str, envelope: dict, *, qos: int = 1, retain: bool = True) -> None:
        """Configure the Last Will. Must be called before :meth:`start`."""
        if self._connected.is_set():
            raise ContractError("set_will() must be called before start()")
        self._client.will_set(topic, json.dumps(envelope).encode("utf-8"), qos, retain)

    def start(self, *, connect_timeout_s: float = 5.0) -> None:
        """Connect (retrying per :class:`ReconnectBackoff`) and start the network loop."""
        self._connect_with_backoff()
        self._client.loop_start()
        if not self._connected.wait(timeout=connect_timeout_s):
            log.warning(
                "CONNACK not observed within timeout; relying on the client's own reconnect",
                extra=ctx(host=self._host, port=self._port, timeout_s=connect_timeout_s),
            )

    def stop(self) -> None:
        try:
            self._client.loop_stop()
        finally:
            self._client.disconnect()
            self._connected.clear()

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def _connect_with_backoff(self) -> None:
        attempts = 0
        while True:
            try:
                self._client.connect(self._host, self._port, self._keepalive_s)
                return
            except OSError as exc:
                attempts += 1
                if self._max_attempts is not None and attempts >= self._max_attempts:
                    raise
                delay = self._backoff.next_delay()
                log.warning("mqtt connect failed, retrying", extra=ctx(
                    host=self._host, port=self._port, attempt=attempts, delay_s=delay, error=str(exc)
                ))
                self._sleep(delay)

    # ------------------------------------------------------------------ MessageBus API
    def publish(self, topic: str, envelope: dict, *, qos: int = 0, retain: bool = False) -> None:
        payload = json.dumps(envelope).encode("utf-8")
        self._client.publish(topic, payload, qos, retain)

    def subscribe(self, topic_filter: str, handler: Handler) -> None:
        pattern = compile_topic_filter(topic_filter)
        self._subs.append((topic_filter, pattern, handler))
        if self._connected.is_set():
            self._client.subscribe(topic_filter, 1)

    # ------------------------------------------------------------------ paho callbacks
    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc != 0:
            log.warning("mqtt connect callback reported failure", extra=ctx(rc=rc))
            return
        self._connected.set()
        self._backoff.reset()
        for topic_filter, _pattern, _handler in self._subs:
            self._client.subscribe(topic_filter, 1)

    def _on_disconnect(self, client, userdata, rc, properties=None) -> None:
        self._connected.clear()
        if rc != 0:
            log.warning("mqtt disconnected unexpectedly", extra=ctx(rc=rc))

    def _on_message(self, client, userdata, msg) -> None:
        try:
            envelope = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            log.warning("dropped malformed JSON payload (E101)", extra=ctx(topic=msg.topic, error=str(exc)))
            return
        for _topic_filter, pattern, handler in self._subs:
            if pattern.match(msg.topic):
                try:
                    handler(msg.topic, envelope)
                except Exception:  # noqa: BLE001 - dispatch boundary: one bad handler must not kill the loop
                    log.exception("subscriber handler raised", extra=ctx(topic=msg.topic))
