"""P4.16: msfc.analytics integrates with the REAL, unmodified P1 domain events (not stand-ins)
-- ProductDetectedEvent/ProductSortedEvent/StateChangedEvent/FaultReport exactly as
msfc.sim.SimCellController already produces them, proving the factory functions in
msfc.analytics.events work against the actual domain objects other layers construct, not just
hand-crafted test doubles.
"""

from __future__ import annotations

import pytest

from msfc.domain import (
    FaultCode,
    FaultReport,
    FaultSeverity,
    MachineState,
    ProductDetectedEvent,
    ProductSortedEvent,
    SortAction,
    SortReason,
    StateChangedEvent,
)
from msfc.analytics.events import from_fault_report, from_product_detected, from_product_sorted, from_state_changed
from msfc.analytics.monitor import MachineMonitor
from msfc.analytics.session import ProductionSession, SessionConfig


def test_a_realistic_production_run_through_real_domain_events() -> None:
    """Boot -> self-test -> running -> 3 products (2 GOOD, 1 DEFECT) -> comm fault -> recovery,
    expressed entirely as the real msfc.domain event types, fed through msfc.analytics."""
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000, name="integration")
    session = ProductionSession(config, started_at_mono_ms=0)  # default initial_state=BOOT
    monitor = MachineMonitor(session)

    boot_to_idle = StateChangedEvent(from_state=MachineState.BOOT, to_state=MachineState.IDLE, cause="self_test_ok")
    monitor.apply_many(from_state_changed(boot_to_idle, mono_ms=0))

    idle_to_running = StateChangedEvent(from_state=MachineState.IDLE, to_state=MachineState.RUNNING, cause="start_cmd")
    monitor.apply_many(from_state_changed(idle_to_running, mono_ms=0))

    products = (
        (ProductDetectedEvent(product_id="7-1", t_detect_mono_ms=0),
         ProductSortedEvent(product_id="7-1", action=SortAction.PASSED, reason=SortReason.VERDICT_GOOD,
                             verdict_received=True, t_detect_mono_ms=0, t_s2_mono_ms=1_000, t_verdict_rx_mono_ms=500)),
        (ProductDetectedEvent(product_id="7-2", t_detect_mono_ms=1_000),
         ProductSortedEvent(product_id="7-2", action=SortAction.PASSED, reason=SortReason.VERDICT_GOOD,
                             verdict_received=True, t_detect_mono_ms=1_000, t_s2_mono_ms=2_000, t_verdict_rx_mono_ms=1_500)),
        (ProductDetectedEvent(product_id="7-3", t_detect_mono_ms=2_000),
         ProductSortedEvent(product_id="7-3", action=SortAction.REJECTED, reason=SortReason.VERDICT_DEFECT,
                             verdict_received=True, t_detect_mono_ms=2_000, t_s2_mono_ms=3_000, t_verdict_rx_mono_ms=2_500)),
    )
    for detected, sorted_event in products:
        monitor.apply(from_product_detected(detected))
        monitor.apply_many(from_product_sorted(sorted_event))

    fault_code = FaultCode(code="F010", name="COMM_LOSS_EDGE", severity=FaultSeverity.FAULT, latching=True,
                            description="edge heartbeat timeout")
    running_to_fault = StateChangedEvent(from_state=MachineState.RUNNING, to_state=MachineState.FAULT, cause="F010")
    monitor.apply(from_fault_report(FaultReport(fault=fault_code, event="RAISED", detail="heartbeat timeout"),
                                     mono_ms=3_000))
    monitor.apply_many(from_state_changed(running_to_fault, mono_ms=3_000))

    fault_to_idle = StateChangedEvent(from_state=MachineState.FAULT, to_state=MachineState.IDLE, cause="reset_cmd")
    monitor.apply(from_fault_report(FaultReport(fault=fault_code, event="CLEARED"), mono_ms=4_000))
    monitor.apply_many(from_state_changed(fault_to_idle, mono_ms=4_000))

    status = monitor.status(now_mono_ms=4_000)
    assert status.cycle_count == 3
    assert status.good_count == 2
    assert status.defect_count == 1
    assert status.downtime_ms == 1_000  # the FAULT window, 3_000 -> 4_000
    assert status.current_fault is None  # cleared before the snapshot
    assert status.oee.quality == pytest.approx(2 / 3)
