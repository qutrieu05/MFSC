"""DemoSession: the dashboard's backend adapter, exercised directly (no HTTP layer)."""

from __future__ import annotations

from pathlib import Path

import pytest

from msfc.dashboard.session import DemoSession


@pytest.fixture()
def session(repo_root: Path) -> DemoSession:
    return DemoSession(contracts_root=repo_root / "contracts")


def test_session_boots_to_idle(session: DemoSession) -> None:
    assert session.sim.state.value == "IDLE"
    assert session.runtime.runtime_state.value == "READY"


def test_send_start_reaches_running(session: DemoSession) -> None:
    session.send_start()
    assert session.sim.state.value == "RUNNING"
    assert session.runtime.runtime_state.value == "RUNNING"


def test_simulate_good_passes(session: DemoSession) -> None:
    session.send_start()
    session.simulate_good()
    trace = session.runtime.product_history()[-1]
    assert trace.outcome.value == "GOOD"
    assert trace.sorted_event.action.value == "PASSED"


def test_simulate_defect_is_rejected(session: DemoSession) -> None:
    session.send_start()
    session.simulate_defect()
    trace = session.runtime.product_history()[-1]
    assert trace.outcome.value == "DEFECT"
    assert trace.sorted_event.action.value == "REJECTED"


def test_simulate_uncertain_resolves_per_fail_closed_policy(session: DemoSession) -> None:
    session.send_start()
    session.simulate_uncertain()
    trace = session.runtime.product_history()[-1]
    assert trace.inspection.verdict.value == "UNCERTAIN"
    assert trace.outcome.value == "DEFECT"  # DecisionPolicy default: uncertain -> DEFECT


def test_simulate_ocr_failure_leaves_ocr_channel_unavailable_but_restores_after(session: DemoSession) -> None:
    session.send_start()
    session.simulate_good()  # baseline: OCR normally available
    assert session.runtime.product_history()[-1].label is not None

    session.simulate_ocr_failure()
    failed_trace = session.runtime.product_history()[-1]
    assert failed_trace.label is None
    assert failed_trace.inspection is not None  # vision alone still decided

    session.simulate_good()  # OCR config must be restored afterwards
    assert session.runtime.product_history()[-1].label is not None


def test_simulate_health_warning_and_critical(session: DemoSession) -> None:
    session.simulate_health_warning()
    assert session.health_monitor.snapshot(mono_ms=session.mono_ms).health_state.value == "WARNING"
    session.simulate_health_critical()
    assert session.health_monitor.snapshot(mono_ms=session.mono_ms).health_state.value == "CRITICAL"
    session.simulate_health_recovery()
    assert session.health_monitor.snapshot(mono_ms=session.mono_ms).health_state.value == "HEALTHY"


def test_simulate_safety_stop_and_recovery(session: DemoSession) -> None:
    session.send_start()
    session.simulate_safety_stop()
    assert session.sim.state.value == "ESTOP"
    assert session.runtime.runtime_state.value == "SAFE_STOP"

    session.send_reset()
    assert session.sim.state.value == "IDLE"
    session.send_start()
    assert session.sim.state.value == "RUNNING"


def test_safety_stop_denies_a_product_without_running_vision(session: DemoSession) -> None:
    session.send_start()
    session.simulate_safety_stop()
    session.simulate_good()  # still callable -- must be denied, not silently skipped
    trace = session.runtime.product_history()[-1]
    assert trace.outcome.value == "SAFETY_DENIED"
    assert trace.inspection is None


def test_background_tick_never_causes_a_spurious_comm_loss_fault(session: DemoSession) -> None:
    """The exact bug class caught while building the standalone Phase 6 demo script (see
    DECISIONS.md) -- repeated background ticks alone must never fault the cell."""
    session.send_start()
    for _ in range(50):
        session.background_tick()
    assert session.sim.state.value == "RUNNING"
    assert "F010" not in session.runtime.snapshot(mono_ms=session.mono_ms).active_fault_codes


def test_run_full_demo_produces_a_deterministic_sequence(session: DemoSession) -> None:
    session.run_full_demo()
    history = session.runtime.product_history()
    assert len(history) >= 4  # at least the scripted GOOD/GOOD/DEFECT/denied-during-estop products
    assert session.runtime.snapshot(mono_ms=session.mono_ms).runtime_state.value == "RUNNING"  # resumed at the end
