"""Cell Controller events: product detection/sorting and state transitions.

Mirrors product_detected.v1, product_sorted.v1 and state_changed.v1
(contracts/schemas/). All timestamps are the Cell Controller's own monotonic clock in
milliseconds (ARCHITECTURE.md section 5.1) — comparing them across devices is meaningless,
only differences within one device's stream are.
"""

from __future__ import annotations

from dataclasses import dataclass

from msfc.core.errors import DomainError
from msfc.domain import _validators as v
from msfc.domain.enums import MachineState, SortAction, SortReason


@dataclass(frozen=True, slots=True)
class ProductDetectedEvent:
    """A product crossed sensor S1; the Cell Controller has issued it a ``product_id``."""

    product_id: str
    t_detect_mono_ms: int
    sensor: str = "S1"
    speed_setpoint_pct: float | None = None

    def __post_init__(self) -> None:
        v.product_id(self.product_id)
        v.non_negative_ms(self.t_detect_mono_ms, field="t_detect_mono_ms")
        if self.sensor != "S1":
            raise DomainError(f"sensor must be 'S1', got {self.sensor!r}")
        if self.speed_setpoint_pct is not None:
            if not (0.0 <= self.speed_setpoint_pct <= 100.0):
                raise DomainError(f"speed_setpoint_pct must be in [0, 100], got {self.speed_setpoint_pct!r}")


@dataclass(frozen=True, slots=True)
class ProductSortedEvent:
    """A product reached S2 and the Cell Controller decided PASSED or REJECTED.

    ``margin_ms`` (``t_s2_mono_ms - t_verdict_rx_mono_ms``) must be positive for every
    product that received a verdict — see NFR-PERF-01 and ADR-0005.
    """

    product_id: str
    action: SortAction
    reason: SortReason
    verdict_received: bool
    t_detect_mono_ms: int
    t_s2_mono_ms: int
    t_verdict_rx_mono_ms: int | None = None
    t_push_mono_ms: int | None = None

    def __post_init__(self) -> None:
        v.product_id(self.product_id)
        v.non_negative_ms(self.t_detect_mono_ms, field="t_detect_mono_ms")
        v.non_negative_ms(self.t_s2_mono_ms, field="t_s2_mono_ms")
        if self.t_verdict_rx_mono_ms is not None:
            v.non_negative_ms(self.t_verdict_rx_mono_ms, field="t_verdict_rx_mono_ms")
        if self.t_push_mono_ms is not None:
            v.non_negative_ms(self.t_push_mono_ms, field="t_push_mono_ms")
        if self.verdict_received and self.t_verdict_rx_mono_ms is None:
            raise DomainError("verdict_received is True but t_verdict_rx_mono_ms is missing")
        if not self.verdict_received and self.t_verdict_rx_mono_ms is not None:
            raise DomainError("verdict_received is False but t_verdict_rx_mono_ms is set")
        if self.t_s2_mono_ms < self.t_detect_mono_ms:
            raise DomainError("t_s2_mono_ms must not be before t_detect_mono_ms")
        if self.t_verdict_rx_mono_ms is not None and self.t_verdict_rx_mono_ms < self.t_detect_mono_ms:
            raise DomainError("t_verdict_rx_mono_ms must not be before t_detect_mono_ms")

    @property
    def latency_detect_to_verdict_ms(self) -> int | None:
        """``t_verdict_rx - t_detect``; None when no verdict arrived (FR-CNV-09)."""
        if self.t_verdict_rx_mono_ms is None:
            return None
        return self.t_verdict_rx_mono_ms - self.t_detect_mono_ms

    @property
    def margin_ms(self) -> int | None:
        """``t_s2 - t_verdict_rx``; must be > 0 for every product (NFR-PERF-01)."""
        if self.t_verdict_rx_mono_ms is None:
            return None
        return self.t_s2_mono_ms - self.t_verdict_rx_mono_ms


@dataclass(frozen=True, slots=True)
class StateChangedEvent:
    """Cell Controller machine-state transition (state_changed.v1)."""

    from_state: MachineState
    to_state: MachineState
    cause: str

    def __post_init__(self) -> None:
        v.non_empty_str(self.cause, field="cause", max_len=120)
