"""P5.7 health score."""

from __future__ import annotations

from msfc.analytics.health_models import AnomalyResult, AnomalySeverity, HealthState, SensorType
from msfc.analytics.health_score import compute_health_score, unknown_health_score


def _anomaly(severity: AnomalySeverity) -> AnomalyResult:
    return AnomalyResult(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=0, severity=severity,
                          kind="deviation", reason="test")


def test_no_anomalies_scores_perfect() -> None:
    score = compute_health_score([])
    assert score.value == 1.0
    assert score.state is HealthState.HEALTHY
    assert score.contributing_reasons == ()


def test_score_decreases_with_severity() -> None:
    warning = compute_health_score([_anomaly(AnomalySeverity.WARNING)])
    anomaly = compute_health_score([_anomaly(AnomalySeverity.ANOMALY)])
    critical = compute_health_score([_anomaly(AnomalySeverity.CRITICAL)])
    assert warning.value > anomaly.value > critical.value


def test_score_is_never_negative_even_with_many_critical_anomalies() -> None:
    anomalies = [_anomaly(AnomalySeverity.CRITICAL) for _ in range(10)]
    score = compute_health_score(anomalies)
    assert score.value == 0.0


def test_score_state_matches_combine_anomalies() -> None:
    score = compute_health_score([_anomaly(AnomalySeverity.CRITICAL), _anomaly(AnomalySeverity.WARNING)])
    assert score.state is HealthState.CRITICAL  # max severity wins, same as P5.8


def test_score_reasons_are_carried_through() -> None:
    score = compute_health_score([_anomaly(AnomalySeverity.WARNING)])
    assert score.contributing_reasons == ("test",)


def test_unknown_health_score_uses_unknown_state() -> None:
    score = unknown_health_score("sensor not yet reporting")
    assert score.state is HealthState.UNKNOWN
    assert "sensor not yet reporting" in score.contributing_reasons
