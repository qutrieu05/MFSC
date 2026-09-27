"""MQTT-style topic filter matching, shared by InMemoryBus and MqttBus.

Supports the two MQTT wildcards: ``+`` (exactly one level) and a trailing ``/#`` (zero or
more remaining levels, matching the broker's own semantics for e.g. ``sport/#`` matching
both ``sport`` and ``sport/tennis/player1``). ``#`` is only accepted as the final segment.
"""

from __future__ import annotations

import re

from msfc.core.errors import ContractError


def compile_topic_filter(topic_filter: str) -> re.Pattern[str]:
    """Compile an MQTT subscription filter (e.g. ``factory/line01/conveyor/+/event/#``)."""
    if topic_filter == "#":
        return re.compile(r"^.*$")
    multi_level = topic_filter.endswith("/#")
    base = topic_filter[:-2] if multi_level else topic_filter
    if "#" in base:
        raise ContractError(f"'#' is only allowed as the final level of a filter: {topic_filter!r}")
    segments = base.split("/")
    parts = [r"[^/]+" if segment == "+" else re.escape(segment) for segment in segments]
    pattern = "^" + "/".join(parts)
    pattern += r"(?:/.*)?$" if multi_level else "$"
    return re.compile(pattern)
