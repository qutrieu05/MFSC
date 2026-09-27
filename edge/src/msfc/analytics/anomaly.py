"""Deterministic anomaly detection (P5.6) and severity combination (P5.8).

Four detector kinds, as named in the PO's directive:
  - "threshold"/"deviation" (unified here -- a baseline's [expected_min, expected_max] range
    IS the threshold; there is no separate concept to duplicate)
  - "trend" (rate_of_change against a configured limit)
  - "sensor_quality" (too many non-OK measurements in a window)

Combining multiple simultaneous anomalies (P5.8) always takes the MAXIMUM severity present --
never an average, a vote, or "AI judgment" -- see AnomalySeverity.rank.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from msfc.core.errors import HealthError
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.health_models import (
    AnomalyResult,
    AnomalySeverity,
    FeatureSet,
    HealthState,
    SensorMeasurement,
    SensorQuality,
    SensorType,
)


@dataclass(frozen=True, slots=True)
class AnomalyThresholds:
    """Every number here is a required, explicit configuration value (P5.6: "avoid arbitrary
    thresholds without documentation") -- there is no built-in default."""

    warning_deviation: float
    anomaly_deviation: float
    critical_deviation: float
    trend_rate_of_change_limit: float | None = None  # abs(rate_of_change) beyond which -> WARNING
    max_bad_quality_ratio: float = 0.5  # fraction of non-OK readings in a window -> sensor_quality anomaly

    def __post_init__(self) -> None:
        if not (0.0 <= self.warning_deviation <= self.anomaly_deviation <= self.critical_deviation):
            raise HealthError(
                "thresholds must satisfy 0 <= warning_deviation <= anomaly_deviation <= critical_deviation, "
                f"got ({self.warning_deviation}, {self.anomaly_deviation}, {self.critical_deviation})"
            )
        if not (0.0 <= self.max_bad_quality_ratio <= 1.0):
            raise HealthError(f"max_bad_quality_ratio must be in [0, 1], got {self.max_bad_quality_ratio!r}")


def _severity_for_magnitude(magnitude: float, thresholds: AnomalyThresholds) -> AnomalySeverity | None:
    if magnitude >= thresholds.critical_deviation:
        return AnomalySeverity.CRITICAL
    if magnitude >= thresholds.anomaly_deviation:
        return AnomalySeverity.ANOMALY
    if magnitude >= thresholds.warning_deviation:
        return AnomalySeverity.WARNING
    return None


def detect_baseline_anomaly(feature: FeatureSet, baseline: HealthBaseline,
                             thresholds: AnomalyThresholds) -> AnomalyResult | None:
    """Threshold/deviation-from-baseline anomaly (P5.6).

    Uses the window's MOST EXTREME value (max above expected_max, or min below expected_min),
    not the mean -- averaging a brief spike together with several normal readings dilutes it
    below any reasonable threshold, which would silently miss exactly the "spike" scenarios
    P5.13/P5.14 ask this to catch (found via manual smoke-testing before writing the test
    suite, same discipline as D-039/D-044/D-049's earlier-round bug catches). A sustained
    *trend* away from baseline is a separate concern, handled by detect_trend_anomaly().
    """
    if feature.sample_count == 0 or feature.minimum is None or feature.maximum is None:
        return None
    deviation_high = baseline.deviation(feature.maximum)
    deviation_low = baseline.deviation(feature.minimum)
    deviation = deviation_high if abs(deviation_high) >= abs(deviation_low) else deviation_low
    extreme_value = feature.maximum if deviation is deviation_high else feature.minimum
    severity = _severity_for_magnitude(abs(deviation), thresholds)
    if severity is None:
        return None
    return AnomalyResult(
        sensor_id=feature.sensor_id, sensor_type=feature.sensor_type, mono_ms=feature.window_end_mono_ms,
        severity=severity, kind="deviation",
        reason=f"extreme value {extreme_value:.3g} deviates {deviation:.3g} from baseline "
               f"[{baseline.expected_min:.3g}, {baseline.expected_max:.3g}]",
        value=extreme_value, threshold=thresholds.critical_deviation,
    )


def detect_trend_anomaly(feature: FeatureSet, thresholds: AnomalyThresholds) -> AnomalyResult | None:
    if thresholds.trend_rate_of_change_limit is None or feature.rate_of_change is None:
        return None
    if abs(feature.rate_of_change) < thresholds.trend_rate_of_change_limit:
        return None
    return AnomalyResult(
        sensor_id=feature.sensor_id, sensor_type=feature.sensor_type, mono_ms=feature.window_end_mono_ms,
        severity=AnomalySeverity.WARNING, kind="trend",
        reason=f"rate_of_change {feature.rate_of_change:.3g}/ms exceeds limit "
               f"{thresholds.trend_rate_of_change_limit:.3g}/ms",
        value=feature.rate_of_change, threshold=thresholds.trend_rate_of_change_limit,
    )


def detect_quality_anomaly(measurements: Sequence[SensorMeasurement], *, sensor_id: str,
                            sensor_type: SensorType, mono_ms: int,
                            thresholds: AnomalyThresholds) -> AnomalyResult | None:
    if not measurements:
        return None
    bad = sum(1 for m in measurements if m.quality is not SensorQuality.OK)
    ratio = bad / len(measurements)
    if ratio < thresholds.max_bad_quality_ratio:
        return None
    return AnomalyResult(
        sensor_id=sensor_id, sensor_type=sensor_type, mono_ms=mono_ms, severity=AnomalySeverity.WARNING,
        kind="sensor_quality", reason=f"{bad}/{len(measurements)} measurements were not OK quality",
        value=ratio, threshold=thresholds.max_bad_quality_ratio,
    )


def combine_anomalies(anomalies: Sequence[AnomalyResult]) -> HealthState:
    """P5.8: the final health state is always the MAXIMUM severity among current anomalies,
    never an average/vote. No anomalies at all -> HEALTHY (not UNKNOWN -- UNKNOWN is reserved
    for "we couldn't evaluate," a distinct condition; see health_monitor.py)."""
    if not anomalies:
        return HealthState.HEALTHY
    worst = max(anomalies, key=lambda a: a.severity.rank).severity
    return {
        AnomalySeverity.INFO: HealthState.HEALTHY,
        AnomalySeverity.WARNING: HealthState.WARNING,
        AnomalySeverity.ANOMALY: HealthState.ANOMALY,
        AnomalySeverity.CRITICAL: HealthState.CRITICAL,
    }[worst]
