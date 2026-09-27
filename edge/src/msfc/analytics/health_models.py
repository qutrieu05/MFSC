"""Machine-health domain model (P5.1, FR-HLT).

Lives inside ``msfc.analytics`` rather than a new top-level package — ARCHITECTURE.md section
7.2 already assigns "tinh OEE, phan tich suc khoe" (OEE calculation AND health analysis) to
this one Layer-7 package for phases 4 *and* 5, and ``edge/tests/unit/test_layer_dependencies.py``
has no separate "health" entry. Building a new package here would be exactly the kind of
"duplicate/conflicting" structure the PO's Phase 5 directive says to avoid.

D-051 (DECISIONS.md): ``HealthState`` here has 5 values (HEALTHY/WARNING/ANOMALY/CRITICAL/
UNKNOWN) per this round's explicit P5.1 instruction — conflicting with
``contracts/schemas/health_state.v1.json`` (Phase 0 draft, 4 values: NORMAL/WARNING/CRITICAL/
UNKNOWN, no ANOMALY). Flagged, not silently resolved; see D-051 for the documented mapping
used when serializing toward that draft schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from msfc.core.errors import HealthError


class SensorType(str, Enum):
    """A superset of contracts/schemas/health_features.v1.json's draft 3-value enum
    (vibration/temperature/current) — this round's P5.2 explicitly names more types; see D-051."""

    TEMPERATURE = "temperature"
    VIBRATION = "vibration"
    CURRENT = "current"
    VOLTAGE = "voltage"
    MOTOR_SPEED = "motor_speed"
    CYCLE_TIME = "cycle_time"
    PRESSURE = "pressure"
    GENERIC = "generic"


class SensorQuality(str, Enum):
    """Every measurement gets exactly one of these (P5.3: "every measurement should have an
    explicit quality/status") — never silently treated as OK when it isn't."""

    OK = "OK"
    MISSING = "MISSING"
    INVALID = "INVALID"  # NaN, infinity, or a value outside the physically possible range
    STALE = "STALE"
    FUTURE_TIMESTAMP = "FUTURE_TIMESTAMP"
    DUPLICATE = "DUPLICATE"
    INVALID_UNIT = "INVALID_UNIT"
    UNAVAILABLE = "UNAVAILABLE"  # the sensor/source itself could not be read


@dataclass(frozen=True, slots=True)
class SensorMeasurement:
    """One raw reading (P5.1/P5.2). ``mono_ms`` is always caller-supplied — msfc.analytics
    never reads the host clock (same discipline as P4's MachineEvent)."""

    sensor_id: str
    sensor_type: SensorType
    mono_ms: int
    value: float
    unit: str
    quality: SensorQuality = SensorQuality.OK

    def __post_init__(self) -> None:
        if self.mono_ms < 0:
            raise HealthError(f"mono_ms must be >= 0, got {self.mono_ms!r}")
        if not self.sensor_id:
            raise HealthError("sensor_id must not be empty")


@dataclass(frozen=True, slots=True)
class FeatureSet:
    """P5.4's feature extraction output for one window of measurements from one sensor.
    Every field is optional (None) when there isn't enough data to compute it — never a fake
    0.0 standing in for "unknown" (P5.3/P5.15: don't silently convert bad/missing data)."""

    sensor_id: str
    sensor_type: SensorType
    window_start_mono_ms: int
    window_end_mono_ms: int
    sample_count: int
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    median: float | None = None
    std_dev: float | None = None
    variance: float | None = None
    value_range: float | None = None
    rate_of_change: float | None = None  # (last - first) / (t_last - t_first), unit/ms
    moving_average: float | None = None
    rms: float | None = None  # meaningful for vibration; None for other sensor types
    deviation_from_baseline: float | None = None  # filled in by baseline.py, not features.py


class AnomalySeverity(str, Enum):
    """P5.8 — deterministic, ordered severity. Order matters: combining multiple simultaneous
    anomalies (P5.8) always takes the maximum severity present, never an average or vote."""

    INFO = "INFO"
    WARNING = "WARNING"
    ANOMALY = "ANOMALY"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return (AnomalySeverity.INFO, AnomalySeverity.WARNING, AnomalySeverity.ANOMALY,
                AnomalySeverity.CRITICAL).index(self)


@dataclass(frozen=True, slots=True)
class AnomalyResult:
    """One detector's finding for one sensor at one point in time (P5.6)."""

    sensor_id: str
    sensor_type: SensorType
    mono_ms: int
    severity: AnomalySeverity
    kind: str  # "threshold" | "deviation" | "trend" | "sensor_quality"
    reason: str
    value: float | None = None
    threshold: float | None = None


class HealthState(str, Enum):
    """P5.1's 5-value state — see this module's docstring (D-051) for the documented
    conflict with the Phase 0 draft schema's 4-value NORMAL/WARNING/CRITICAL/UNKNOWN."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    ANOMALY = "ANOMALY"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class HealthScore:
    """P5.7: a single software health indicator, 0.0 (worst) to 1.0 (best) — this
    representation, not 0-100, is the one this implementation documents and uses throughout.

    THIS IS A SOFTWARE INDICATOR DERIVED FROM DETERMINISTIC RULES, NOT A CALIBRATED PHYSICAL
    HEALTH MEASUREMENT. It has not been validated against any real machine's actual condition
    or failure history (P5.7: "do NOT pretend the score represents actual physical machine
    health until calibrated using real machine data").
    """

    value: float
    state: HealthState
    contributing_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise HealthError(f"HealthScore.value must be in [0, 1], got {self.value!r}")


class HealthEventType(str, Enum):
    SENSOR_READING = "sensor_reading"
    ANOMALY_DETECTED = "anomaly_detected"
    ANOMALY_CLEARED = "anomaly_cleared"
    HEALTH_STATE_CHANGED = "health_state_changed"
    HEALTH_SCORE_CHANGED = "health_score_changed"
    SENSOR_FAULT = "sensor_fault"
    MACHINE_HEALTH_WARNING = "machine_health_warning"
    MACHINE_HEALTH_CRITICAL = "machine_health_critical"


@dataclass(frozen=True, slots=True)
class HealthEvent:
    """P5.9 — deliberately its own type, not a reuse-by-force of
    :class:`msfc.analytics.events.MachineEvent` (different vocabulary, different producer),
    but structurally identical (type/mono_ms/detail) so a future combined event stream is a
    trivial merge, not a rewrite."""

    type: HealthEventType
    mono_ms: int
    sensor_id: str | None = None
    detail: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mono_ms < 0:
            raise HealthError(f"mono_ms must be >= 0, got {self.mono_ms!r}")
