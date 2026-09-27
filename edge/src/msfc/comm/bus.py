"""MessageBus interface (IF-07) and an in-process implementation for tests and the simulator.

``msfc.vision``, ``msfc.decision`` and ``msfc.domain`` never import this module — only
``msfc.services``, ``msfc.sim`` and ``msfc.dashboard`` talk to a bus (ARCHITECTURE.md
section 7.2). Business logic is written against the :class:`MessageBus` protocol so it
runs unchanged over :class:`InMemoryBus` (tests, P1.6 simulator) or :class:`MqttBus`
(a real broker, once Mosquitto is installed — see PHASE1_PLAN.md P1.9).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

from msfc.comm.topic_match import compile_topic_filter

Handler = Callable[[str, dict], None]
"""A subscription callback: ``handler(topic, envelope)``. Envelopes are already-decoded
dicts (see MqttBus for the JSON boundary); handlers do not see raw bytes."""


@runtime_checkable
class MessageBus(Protocol):
    """What every layer above L5 depends on — never a concrete broker client."""

    def publish(self, topic: str, envelope: dict, *, qos: int = 0, retain: bool = False) -> None:
        """Publish *envelope* (already schema-checked by the caller) to *topic*."""

    def subscribe(self, topic_filter: str, handler: Handler) -> None:
        """Register *handler* for every topic matching *topic_filter* (``+``/``#`` allowed).

        If any retained message already published matches the filter, the bus delivers it
        to *handler* immediately, mirroring real MQTT retain semantics.
        """

    def start(self) -> None:
        """Begin delivering messages (no-op for :class:`InMemoryBus`)."""

    def stop(self) -> None:
        """Stop delivering messages and release resources."""


@dataclass(slots=True)
class PublishedMessage:
    """One recorded publish, for test assertions against :attr:`InMemoryBus.published`."""

    topic: str
    envelope: dict
    qos: int
    retain: bool


@dataclass(slots=True)
class _Subscription:
    pattern: re.Pattern[str]
    handler: Handler


class InMemoryBus:
    """Synchronous, in-process pub/sub bus (FR-SRV-03: a test double, not a toy).

    Delivery is synchronous and in subscription order — deterministic on purpose, so tests
    (and the P1.6 simulator/decision pipeline) do not need to sleep or poll for messages.
    """

    def __init__(self) -> None:
        self._subs: list[_Subscription] = []
        self._published: list[PublishedMessage] = []
        self._retained: dict[str, dict] = {}
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False
        self._subs.clear()

    def publish(self, topic: str, envelope: dict, *, qos: int = 0, retain: bool = False) -> None:
        self._published.append(PublishedMessage(topic=topic, envelope=envelope, qos=qos, retain=retain))
        if retain:
            self._retained[topic] = envelope
        for sub in tuple(self._subs):  # snapshot: a handler may subscribe/publish reentrantly
            if sub.pattern.match(topic):
                sub.handler(topic, envelope)

    def subscribe(self, topic_filter: str, handler: Handler) -> None:
        pattern = compile_topic_filter(topic_filter)  # validated eagerly so bad filters fail fast
        self._subs.append(_Subscription(pattern=pattern, handler=handler))
        for topic, envelope in self._retained.items():
            if pattern.match(topic):
                handler(topic, envelope)

    @property
    def published(self) -> tuple[PublishedMessage, ...]:
        """Every message published so far, in order — for test assertions."""
        return tuple(self._published)

    def clear_published(self) -> None:
        self._published.clear()
