"""Availability / Performance / Quality / OEE calculations (P4.5-P4.8).

Every function raises :class:`OeeError` rather than silently returning a misleading number for
invalid input (zero/negative planned time, zero run time with nonzero count, etc.) — "do not
allow invalid data to silently produce misleading metrics" (P4.5). No intermediate rounding
anywhere in this module; round only at a presentation boundary if one is ever built (P4.8,
P4.19: no dashboard this phase).
"""

from __future__ import annotations

from msfc.core.errors import OeeError
from msfc.analytics.models import OeeResult


def calculate_availability(*, planned_production_time_ms: int, downtime_ms: int) -> float:
    """Availability = Run Time / Planned Production Time."""
    if planned_production_time_ms <= 0:
        raise OeeError(f"planned_production_time_ms must be > 0, got {planned_production_time_ms!r}")
    if downtime_ms < 0:
        raise OeeError(f"downtime_ms must be >= 0, got {downtime_ms!r}")
    run_time_ms = planned_production_time_ms - downtime_ms
    if run_time_ms < 0:
        raise OeeError(
            f"downtime_ms ({downtime_ms}) exceeds planned_production_time_ms ({planned_production_time_ms})"
        )
    return run_time_ms / planned_production_time_ms


def calculate_performance(*, ideal_cycle_time_ms: int, total_count: int, run_time_ms: int) -> float:
    """Performance = (Ideal Cycle Time x Total Count) / Run Time.

    NOT clamped to 1.0 — a real production run whose actual average cycle time beats the
    configured "ideal" is a valid (if unusual) result, not a bug; see D-048, DECISIONS.md, for
    why contracts/schemas/oee_metrics.v1.json's draft `maximum: 1` constraint on this field is
    flagged rather than silently matched.
    """
    if ideal_cycle_time_ms <= 0:
        raise OeeError(f"ideal_cycle_time_ms must be > 0, got {ideal_cycle_time_ms!r}")
    if total_count < 0:
        raise OeeError(f"total_count must be >= 0, got {total_count!r}")
    if run_time_ms <= 0:
        raise OeeError(f"run_time_ms must be > 0, got {run_time_ms!r}")
    return (ideal_cycle_time_ms * total_count) / run_time_ms


def calculate_quality(*, good_count: int, total_count: int) -> float:
    """Quality = Good Count / Total Count.

    D-045 (DECISIONS.md): UNCERTAIN products never reach this calculation — see
    msfc.analytics.events.from_product_sorted's docstring for why (DecisionEngine already
    resolves UNCERTAIN upstream, per existing FR-DEC-04 policy).
    """
    if total_count <= 0:
        raise OeeError(f"total_count must be > 0, got {total_count!r}")
    if good_count < 0 or good_count > total_count:
        raise OeeError(f"good_count must be in [0, total_count={total_count}], got {good_count!r}")
    return good_count / total_count


def calculate_oee(
    *,
    planned_production_time_ms: int,
    downtime_ms: int,
    ideal_cycle_time_ms: int,
    total_count: int,
    good_count: int,
) -> OeeResult:
    """OEE = Availability x Performance x Quality."""
    availability = calculate_availability(
        planned_production_time_ms=planned_production_time_ms, downtime_ms=downtime_ms
    )
    run_time_ms = planned_production_time_ms - downtime_ms
    defect_count = total_count - good_count

    if total_count == 0:
        # Zero production during available run time is meaningful (0% performance/quality),
        # not an error -- unlike a zero *denominator*, which the two functions above already
        # reject explicitly.
        performance = 0.0
        quality = 0.0
    else:
        performance = calculate_performance(
            ideal_cycle_time_ms=ideal_cycle_time_ms, total_count=total_count, run_time_ms=run_time_ms
        )
        quality = calculate_quality(good_count=good_count, total_count=total_count)

    oee = availability * performance * quality
    return OeeResult(
        availability=availability, performance=performance, quality=quality, oee=oee,
        planned_production_time_ms=planned_production_time_ms, run_time_ms=run_time_ms,
        downtime_ms=downtime_ms, total_count=total_count, good_count=good_count, defect_count=defect_count,
    )


def to_oee_metrics_v1_payload(result: OeeResult) -> dict[str, float]:
    """Serialize for contracts/schemas/oee_metrics.v1.json (a Phase-0 DRAFT schema, not yet
    published by anything real — P4.18: contract/interface only, no MQTT broker required).

    Clamps availability/performance/quality/oee to [0, 1] ONLY here, at this wire-payload
    boundary, to satisfy the draft schema's `maximum: 1` constraint on all four fields — the
    underlying :class:`OeeResult` this is built from is never altered. See D-048 (DECISIONS.md)
    for the discovered conflict this resolves.
    """
    def clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    return {
        "availability": clamp(result.availability),
        "performance": clamp(result.performance),
        "quality": clamp(result.quality),
        "oee": clamp(result.oee),
    }
