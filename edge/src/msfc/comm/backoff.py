"""Reconnect backoff for MqttBus (FR-COM-07: "tự kết nối lại với backoff").

Deterministic (no jitter) so tests can assert exact delays; a real deployment with many
devices reconnecting at once might add jitter later — track that as a FUTURE item if it
becomes a problem, not a default.
"""

from __future__ import annotations

from msfc.core.errors import ContractError


class ReconnectBackoff:
    """Exponential backoff with a cap: ``min(base * factor**attempt, max)``."""

    def __init__(self, *, base_s: float = 1.0, factor: float = 2.0, max_s: float = 30.0) -> None:
        if base_s <= 0:
            raise ContractError(f"base_s must be > 0, got {base_s!r}")
        if factor <= 1:
            raise ContractError(f"factor must be > 1, got {factor!r}")
        if max_s < base_s:
            raise ContractError(f"max_s ({max_s!r}) must be >= base_s ({base_s!r})")
        self._base = base_s
        self._factor = factor
        self._max = max_s
        self._attempt = 0

    @property
    def attempt(self) -> int:
        return self._attempt

    def next_delay(self) -> float:
        """Return the delay (seconds) for the current attempt, then advance the counter."""
        delay = min(self._base * (self._factor ** self._attempt), self._max)
        self._attempt += 1
        return delay

    def reset(self) -> None:
        """Call after a successful connection so the next failure starts from ``base_s`` again."""
        self._attempt = 0
