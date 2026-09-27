"""Machine health monitoring layer (P5.10).

    Sensor Data -> Quality Validation -> Feature Extraction -> Baseline -> Anomaly Detection
    -> Health Scoring -> MachineHealthMonitor

Consumes already-quality-tagged :class:`SensorMeasurement` objects (the caller runs
``msfc.analytics.quality.build_measurement`` first) rather than raw values -- the same
separation :class:`msfc.analytics.session.ProductionSession` uses (it consumes pre-built
``MachineEvent``s, it doesn't construct them), reused here rather than reinvented (P5.16).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from msfc.core.errors import HealthError
from msfc.analytics.anomaly import (
    AnomalyThresholds,
    detect_baseline_anomaly,
    detect_quality_anomaly,
    detect_trend_anomaly,
)
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.features import extract_features
from msfc.analytics.health_events import from_anomaly, from_health_score_change, from_health_state_change, from_measurement
from msfc.analytics.health_models import (
    AnomalyResult,
    FeatureSet,
    HealthEvent,
    HealthScore,
    HealthState,
    SensorMeasurement,
)
from msfc.analytics.health_score import compute_health_score, unknown_health_score


@dataclass(frozen=True, slots=True)
class MachineHealthSnapshot:
    """P5.10's read model: everything the monitor currently knows, as of ``mono_ms``."""

    mono_ms: int
    latest_measurements: dict[str, SensorMeasurement] = field(default_factory=dict)
    features: dict[str, FeatureSet] = field(default_factory=dict)
    active_anomalies: tuple[AnomalyResult, ...] = ()
    health_score: HealthScore = field(default_factory=lambda: unknown_health_score("no data yet"))
    health_state: HealthState = HealthState.UNKNOWN


class MachineHealthMonitor:
    """``thresholds`` is keyed per ``sensor_id``, not shared globally -- a single threshold
    set can't fit sensors of very different natural scale (a few degC vs a few mm/s vs a few
    A); this mirrors ``baselines`` already being per-sensor. A sensor with no configured
    thresholds is never judged (no anomaly detection runs for it) rather than silently reusing
    another sensor's numbers.

    ``window_ms`` has a direct, visible effect on how fast an anomaly "recovers": since
    detect_baseline_anomaly looks at every reading currently inside the window (not just the
    latest one), a past spike keeps the state anomalous until it ages out of the window, even
    if the most recent readings are back to normal. A larger window smooths out noise but
    recovers slower; a smaller window recovers faster but is noisier -- this is a real,
    intentional tradeoff (P5.14's "anomaly recovery" fixture only shows recovery once the
    window has moved past the anomalous reading), not a bug.
    """

    def __init__(self, *, baselines: dict[str, HealthBaseline], thresholds: dict[str, AnomalyThresholds],
                 window_ms: int = 10_000) -> None:
        if window_ms <= 0:
            raise HealthError(f"window_ms must be > 0, got {window_ms!r}")
        self._baselines = dict(baselines)
        self._thresholds = dict(thresholds)
        self._window_ms = window_ms
        self._history: dict[str, list[SensorMeasurement]] = {}
        self._last_ingested_mono_ms: dict[str, int] = {}
        self._latest_features: dict[str, FeatureSet] = {}
        self._active_anomalies: dict[tuple[str, str], AnomalyResult] = {}
        self._state = HealthState.UNKNOWN
        self._score = unknown_health_score("no data yet")
        self._events: list[HealthEvent] = []

    def ingest(self, measurement: SensorMeasurement, *, mono_ms: int) -> None:
        sensor_id = measurement.sensor_id
        last = self._last_ingested_mono_ms.get(sensor_id)
        if last is not None and mono_ms < last:
            raise HealthError(
                f"out-of-order ingest for sensor_id {sensor_id!r}: mono_ms {mono_ms} is before "
                f"last ingested {last} (P5.15: 'out-of-order timestamps' must fail, not silently reorder)"
            )
        self._last_ingested_mono_ms[sensor_id] = mono_ms
        self._events.append(from_measurement(measurement))

        history = self._history.setdefault(sensor_id, [])
        history.append(measurement)
        cutoff = mono_ms - self._window_ms
        del history[:next((i for i, m in enumerate(history) if m.mono_ms >= cutoff), len(history))]

        window_start = history[0].mono_ms if history else mono_ms
        feature = extract_features(history, sensor_id=sensor_id, sensor_type=measurement.sensor_type,
                                    window_start_mono_ms=window_start, window_end_mono_ms=mono_ms)
        self._latest_features[sensor_id] = feature

        found: list[AnomalyResult] = []
        thresholds = self._thresholds.get(sensor_id)
        if thresholds is not None:
            baseline = self._baselines.get(sensor_id)
            if baseline is not None:
                result = detect_baseline_anomaly(feature, baseline, thresholds)
                if result is not None:
                    found.append(result)
            trend = detect_trend_anomaly(feature, thresholds)
            if trend is not None:
                found.append(trend)
            quality = detect_quality_anomaly(history, sensor_id=sensor_id, sensor_type=measurement.sensor_type,
                                              mono_ms=mono_ms, thresholds=thresholds)
            if quality is not None:
                found.append(quality)

        self._reconcile_anomalies(sensor_id, found)
        self._recompute_score(mono_ms=mono_ms)

    def _reconcile_anomalies(self, sensor_id: str, found: list[AnomalyResult]) -> None:
        found_kinds = {a.kind for a in found}
        for key in [k for k in self._active_anomalies if k[0] == sensor_id and k[1] not in found_kinds]:
            self._events.append(from_anomaly(self._active_anomalies.pop(key), cleared=True))
        for anomaly in found:
            key = (sensor_id, anomaly.kind)
            if key not in self._active_anomalies:
                self._events.append(from_anomaly(anomaly))
            self._active_anomalies[key] = anomaly

    def _recompute_score(self, *, mono_ms: int) -> None:
        old_state, old_score = self._state, self._score
        self._score = compute_health_score(tuple(self._active_anomalies.values()))
        self._state = self._score.state
        if self._state != old_state:
            self._events.extend(from_health_state_change(old_state, self._state, mono_ms=mono_ms))
        if self._score.value != old_score.value:
            self._events.append(from_health_score_change(old_score, self._score, mono_ms=mono_ms))

    def snapshot(self, *, mono_ms: int) -> MachineHealthSnapshot:
        latest = {sid: hist[-1] for sid, hist in self._history.items() if hist}
        return MachineHealthSnapshot(
            mono_ms=mono_ms, latest_measurements=latest, features=dict(self._latest_features),
            active_anomalies=tuple(self._active_anomalies.values()), health_score=self._score,
            health_state=self._state,
        )

    def drain_events(self) -> tuple[HealthEvent, ...]:
        """Returns every event produced since the last call, then clears the buffer -- mirrors
        a typical publish-and-clear outbox, without this module knowing MQTT exists."""
        events = tuple(self._events)
        self._events.clear()
        return events
