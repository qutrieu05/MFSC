"""Deterministic machine baseline (P5.5) — configurable expected operating range per sensor.

No default/hard-coded values for any real machine (none exists yet) — every
:class:`HealthBaseline` is constructed by the caller (a test, a simulation, or eventually a PO-
supplied calibration), never embedded here.
"""

from __future__ import annotations

from dataclasses import dataclass

from msfc.core.errors import HealthError
from msfc.analytics.health_models import SensorType


@dataclass(frozen=True, slots=True)
class HealthBaseline:
    """The expected operating range for one sensor, plus optional reference statistics
    (mean/std dev from a recorded baseline-collection run, FR-HLT-02) for z-score-style
    deviation. Only ``expected_min``/``expected_max`` are required — everything else is
    optional, since a fresh deployment may only have a configured range, not yet a recorded
    reference run."""

    sensor_type: SensorType
    expected_min: float
    expected_max: float
    unit: str = ""
    reference_mean: float | None = None
    reference_std_dev: float | None = None

    def __post_init__(self) -> None:
        if self.expected_min > self.expected_max:
            raise HealthError(
                f"expected_min ({self.expected_min}) must be <= expected_max ({self.expected_max})"
            )
        if self.reference_std_dev is not None and self.reference_std_dev < 0:
            raise HealthError(f"reference_std_dev must be >= 0, got {self.reference_std_dev!r}")

    def deviation(self, value: float) -> float:
        """Signed distance outside [expected_min, expected_max]; 0.0 when inside the range."""
        if value < self.expected_min:
            return value - self.expected_min
        if value > self.expected_max:
            return value - self.expected_max
        return 0.0

    def z_score(self, value: float) -> float | None:
        """None when no reference statistics are configured, or when reference_std_dev is 0
        (a constant reference signal -- any deviation at all would be an infinite z-score,
        which is not a meaningful number to report; callers should fall back to
        :meth:`deviation` in that case)."""
        if self.reference_mean is None or not self.reference_std_dev:
            return None
        return (value - self.reference_mean) / self.reference_std_dev
