"""P6.12: host/simulation timing model tests."""

from __future__ import annotations

import time

import pytest

from msfc.core.errors import OrchestrationError
from msfc.services.timing import PipelineTiming, StageTiming, StageTimer, TimingStats


def test_stage_timing_rejects_negative_duration() -> None:
    with pytest.raises(OrchestrationError):
        StageTiming(stage="vision", duration_ms=-1.0)


def test_pipeline_timing_total_sums_stages() -> None:
    timing = PipelineTiming(product_id="1-0", stages=(
        StageTiming(stage="vision", duration_ms=5.0), StageTiming(stage="decision", duration_ms=1.0),
    ))
    assert timing.total_ms == pytest.approx(6.0)
    assert timing.stage_ms("vision") == pytest.approx(5.0)
    assert timing.stage_ms("missing") is None


def test_stage_timer_measures_real_elapsed_time() -> None:
    timer = StageTimer("1-0")
    with timer.stage("vision"):
        time.sleep(0.01)
    with timer.stage("decision"):
        pass
    timing = timer.finish()
    assert timing.stage_ms("vision") >= 5.0  # generous lower bound, avoids CI flakiness
    assert timing.stage_ms("decision") is not None
    assert timing.total_ms >= timing.stage_ms("vision")


def test_timing_stats_aggregates_across_runs() -> None:
    stats = TimingStats()
    stats.record(PipelineTiming(product_id="1-0", stages=(StageTiming(stage="vision", duration_ms=10.0),)))
    stats.record(PipelineTiming(product_id="1-1", stages=(StageTiming(stage="vision", duration_ms=20.0),)))

    assert stats.count("vision") == 2
    assert stats.average_ms("vision") == pytest.approx(15.0)
    assert stats.min_ms("vision") == pytest.approx(10.0)
    assert stats.max_ms("vision") == pytest.approx(20.0)
    assert stats.count() == 2  # __total__
    assert stats.stages() == ("vision",)


def test_timing_stats_average_is_none_when_never_recorded() -> None:
    stats = TimingStats()
    assert stats.average_ms("vision") is None
    assert stats.count("vision") == 0
