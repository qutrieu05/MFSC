"""P6.12: a host/simulation-only software timing model for the orchestrated pipeline.

IMPORTANT -- READ BEFORE USING THESE NUMBERS FOR ANYTHING:
Every measurement here is wall-clock time taken on THIS development machine while running a
synthetic/simulated pipeline. It says something real about the *relative* cost of stages when
comparing runs on the same host, but it is NOT a measurement of real-time hardware behaviour,
NOT a production throughput claim, and NOT comparable to ``conveyor.telemetry.timing``
(timing_stats.v1) -- that is the *firmware's* own per-control-cycle timing, a completely
different, already-contracted concept this module does not touch or replace.

    HOST / SIMULATION timing  = what this module measures, always.
    REAL HARDWARE timing      = PENDING (no hardware exists -- see PHASE6_COMPLETION_REPORT.md).

Deliberately not wired to any MQTT topic: publishing a new timing schema over MQTT is exactly
the kind of "make it look more built than it is" P6 explicitly warns against, and no schema for
this exists in contracts/ (unlike timing_stats.v1, which is the firmware's, not this module's).
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from msfc.core.errors import OrchestrationError


@dataclass(frozen=True, slots=True)
class StageTiming:
    """One stage's duration for one pipeline run, in milliseconds (host wall-clock)."""

    stage: str
    duration_ms: float

    def __post_init__(self) -> None:
        if self.duration_ms < 0:
            raise OrchestrationError(f"duration_ms must be >= 0, got {self.duration_ms!r}")


@dataclass(frozen=True, slots=True)
class PipelineTiming:
    """All stage timings for one product cycle, plus the total."""

    product_id: str
    stages: tuple[StageTiming, ...]

    @property
    def total_ms(self) -> float:
        return sum(s.duration_ms for s in self.stages)

    def stage_ms(self, stage: str) -> float | None:
        for s in self.stages:
            if s.stage == stage:
                return s.duration_ms
        return None


class StageTimer:
    """Measures one pipeline run's stages, host wall-clock, HOST/SIMULATION ONLY (see module
    docstring). Usage::

        timer = StageTimer(product_id)
        with timer.stage("vision"):
            ...
        with timer.stage("decision"):
            ...
        timing = timer.finish()
    """

    def __init__(self, product_id: str) -> None:
        self._product_id = product_id
        self._stages: list[StageTiming] = []

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self._stages.append(StageTiming(stage=name, duration_ms=(time.perf_counter() - start) * 1000.0))

    def finish(self) -> PipelineTiming:
        return PipelineTiming(product_id=self._product_id, stages=tuple(self._stages))


@dataclass(slots=True)
class TimingStats:
    """Running min/max/count/average per stage across many pipeline runs (P6.12/P6.22:
    "processing counters, timing statistics"). Mutable by design -- it is an accumulator a
    :class:`~msfc.services.runtime.CellRuntime` owns for the lifetime of one process, exactly
    like ``msfc.comm.dedupe.DedupeFilter`` accumulates ``dropped_count``."""

    _count: dict[str, int] = field(default_factory=dict)
    _total_ms: dict[str, float] = field(default_factory=dict)
    _min_ms: dict[str, float] = field(default_factory=dict)
    _max_ms: dict[str, float] = field(default_factory=dict)

    def record(self, timing: PipelineTiming) -> None:
        for stage in timing.stages:
            self._count[stage.stage] = self._count.get(stage.stage, 0) + 1
            self._total_ms[stage.stage] = self._total_ms.get(stage.stage, 0.0) + stage.duration_ms
            self._min_ms[stage.stage] = min(self._min_ms.get(stage.stage, stage.duration_ms), stage.duration_ms)
            self._max_ms[stage.stage] = max(self._max_ms.get(stage.stage, stage.duration_ms), stage.duration_ms)
        total_key = "__total__"
        self._count[total_key] = self._count.get(total_key, 0) + 1
        self._total_ms[total_key] = self._total_ms.get(total_key, 0.0) + timing.total_ms
        self._min_ms[total_key] = min(self._min_ms.get(total_key, timing.total_ms), timing.total_ms)
        self._max_ms[total_key] = max(self._max_ms.get(total_key, timing.total_ms), timing.total_ms)

    def count(self, stage: str = "__total__") -> int:
        return self._count.get(stage, 0)

    def average_ms(self, stage: str = "__total__") -> float | None:
        n = self._count.get(stage, 0)
        if n == 0:
            return None
        return self._total_ms[stage] / n

    def min_ms(self, stage: str = "__total__") -> float | None:
        return self._min_ms.get(stage)

    def max_ms(self, stage: str = "__total__") -> float | None:
        return self._max_ms.get(stage)

    def stages(self) -> tuple[str, ...]:
        return tuple(s for s in self._count if s != "__total__")
