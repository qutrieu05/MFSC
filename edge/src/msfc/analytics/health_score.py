"""Health score (P5.7) — 0.0 (worst) to 1.0 (best), documented and used consistently as that
representation throughout msfc.analytics (never 0-100 anywhere in this codebase).

D-052 (DECISIONS.md): the per-severity penalty weights below are a documented, deterministic,
but ARBITRARY placeholder formula — there is no real machine degradation data yet to calibrate
against (P5.7: "do NOT pretend the score represents actual physical machine health until
calibrated using real machine data"). They exist so the score is reproducible and testable,
not because 0.15/0.35/0.60 are meaningful physical quantities.
"""

from __future__ import annotations

from typing import Sequence

from msfc.analytics.anomaly import combine_anomalies
from msfc.analytics.health_models import AnomalyResult, AnomalySeverity, HealthScore, HealthState

#: Deterministic, documented, NOT physically calibrated (D-052) -- see module docstring.
_SEVERITY_PENALTY: dict[AnomalySeverity, float] = {
    AnomalySeverity.INFO: 0.0,
    AnomalySeverity.WARNING: 0.15,
    AnomalySeverity.ANOMALY: 0.35,
    AnomalySeverity.CRITICAL: 0.60,
}


def compute_health_score(anomalies: Sequence[AnomalyResult]) -> HealthScore:
    """THIS IS A SOFTWARE HEALTH INDICATOR, NOT A CALIBRATED PHYSICAL MEASUREMENT (P5.7)."""
    state = combine_anomalies(anomalies)
    if not anomalies:
        return HealthScore(value=1.0, state=state, contributing_reasons=())
    penalty = sum(_SEVERITY_PENALTY[a.severity] for a in anomalies)
    value = max(0.0, 1.0 - penalty)
    reasons = tuple(a.reason for a in anomalies)
    return HealthScore(value=value, state=state, contributing_reasons=reasons)


def unknown_health_score(reason: str) -> HealthScore:
    """P5.22: for unavailable health prediction, use an explicit UNKNOWN result rather than
    inventing a healthy one. Value is 0.5 (the representation's own midpoint) purely as a
    placeholder for the numeric field -- callers must branch on ``state``, never on ``value``,
    when state is UNKNOWN."""
    return HealthScore(value=0.5, state=HealthState.UNKNOWN, contributing_reasons=(reason,))
