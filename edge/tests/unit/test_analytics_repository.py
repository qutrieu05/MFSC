"""P4.17 OEE persistence abstraction — interface + in-memory implementation only."""

from __future__ import annotations

from msfc.analytics.calculations import calculate_oee
from msfc.analytics.repository import InMemoryOeeSnapshotRepository, OeeSnapshotRepository

_RESULT = calculate_oee(
    planned_production_time_ms=10_000, downtime_ms=0, ideal_cycle_time_ms=1_000, total_count=10, good_count=10,
)


def test_in_memory_repository_satisfies_the_protocol() -> None:
    repo: OeeSnapshotRepository = InMemoryOeeSnapshotRepository()
    assert isinstance(repo, InMemoryOeeSnapshotRepository)


def test_latest_is_none_for_an_unknown_session() -> None:
    repo = InMemoryOeeSnapshotRepository()
    assert repo.latest("unknown") is None
    assert repo.history("unknown") == ()


def test_save_and_latest() -> None:
    repo = InMemoryOeeSnapshotRepository()
    repo.save("shift-a", 1_000, _RESULT)
    mono_ms, result = repo.latest("shift-a")
    assert mono_ms == 1_000
    assert result is _RESULT


def test_history_accumulates_in_order() -> None:
    repo = InMemoryOeeSnapshotRepository()
    repo.save("shift-a", 1_000, _RESULT)
    repo.save("shift-a", 2_000, _RESULT)
    history = repo.history("shift-a")
    assert [t for t, _ in history] == [1_000, 2_000]


def test_sessions_are_isolated_from_each_other() -> None:
    repo = InMemoryOeeSnapshotRepository()
    repo.save("shift-a", 1_000, _RESULT)
    assert repo.latest("shift-b") is None
