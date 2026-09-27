"""MQTT Communication (Layer 5, IF-07): MessageBus and its implementations.

``msfc.vision``, ``msfc.decision`` and ``msfc.domain`` must never import this package —
only ``msfc.services``, ``msfc.sim``, ``msfc.dashboard`` and ``msfc.cli`` talk to a bus
(ARCHITECTURE.md section 7.2).
"""

from __future__ import annotations

from msfc.comm.backoff import ReconnectBackoff
from msfc.comm.bus import Handler, InMemoryBus, MessageBus, PublishedMessage
from msfc.comm.dedupe import DedupeFilter
from msfc.comm.mqtt_bus import MqttBus, MqttClientLike
from msfc.comm.topic_match import compile_topic_filter

__all__ = [
    "MessageBus",
    "Handler",
    "InMemoryBus",
    "PublishedMessage",
    "DedupeFilter",
    "ReconnectBackoff",
    "MqttBus",
    "MqttClientLike",
    "compile_topic_filter",
]
