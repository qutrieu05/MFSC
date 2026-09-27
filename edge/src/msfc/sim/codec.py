"""Domain object -> envelope ``data`` dict, for the handful of message types the Cell
Controller simulator publishes. Kept local to ``msfc.sim`` rather than a shared
"generic domain codec": firmware is C, not Python, so there is no real firmware code to
share this with, and generalising before a second consumer exists would be speculative.
"""

from __future__ import annotations

from msfc.domain import CellStateSnapshot, FaultReport, ProductDetectedEvent, ProductSortedEvent, StateChangedEvent


def product_detected_data(event: ProductDetectedEvent) -> dict:
    data: dict = {
        "product_id": event.product_id,
        "sensor": event.sensor,
        "t_detect_mono_ms": event.t_detect_mono_ms,
    }
    if event.speed_setpoint_pct is not None:
        data["speed_setpoint_pct"] = event.speed_setpoint_pct
    return data


def product_sorted_data(event: ProductSortedEvent) -> dict:
    return {
        "product_id": event.product_id,
        "action": event.action.value,
        "reason": event.reason.value,
        "verdict_received": event.verdict_received,
        "t_detect_mono_ms": event.t_detect_mono_ms,
        "t_verdict_rx_mono_ms": event.t_verdict_rx_mono_ms,
        "t_s2_mono_ms": event.t_s2_mono_ms,
        "t_push_mono_ms": event.t_push_mono_ms,
        "latency_detect_to_verdict_ms": event.latency_detect_to_verdict_ms,
        "margin_ms": event.margin_ms,
    }


def state_changed_data(event: StateChangedEvent) -> dict:
    return {"from": event.from_state.value, "to": event.to_state.value, "cause": event.cause}


def fault_data(report: FaultReport) -> dict:
    return {
        "code": report.fault.code,
        "name": report.fault.name,
        "severity": report.fault.severity.value,
        "event": report.event,
        "latched": report.fault.latching,
        "detail": report.detail,
    }


def cell_state_data(snapshot: CellStateSnapshot) -> dict:
    return {
        "machine_state": snapshot.machine_state.value,
        "active_faults": list(snapshot.active_faults),
        "speed_setpoint_pct": snapshot.speed_setpoint_pct,
        "motor_output_pct": snapshot.motor_output_pct,
        "safety_relay_closed": snapshot.safety_relay_closed,
        "pusher": snapshot.pusher.value,
        "queue_len": snapshot.queue_len,
        "safety_vision_required": snapshot.safety_vision_required,
        "counters": {
            "detected": snapshot.counters.detected,
            "passed": snapshot.counters.passed,
            "rejected": snapshot.counters.rejected,
            "no_decision": snapshot.counters.no_decision,
        },
    }
