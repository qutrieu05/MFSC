"""Dashboard API view-models (section 10: "stable DTO/view-model structures... do not expose
arbitrary internal objects just because they exist").

Every ``from_*`` builder here only READS existing P1-P6 objects (``CellSnapshot``,
``MachineStatus``, ``MachineHealthSnapshot``, ``ProductCycleTrace``, ...) and reshapes them into
a JSON-friendly, UI-focused view -- no field here is computed by re-deriving a verdict, an OEE
number, or a health state; every numeric/enum value is copied straight from the backend that
already calculated it (msfc.decision, msfc.analytics, msfc.sim). The one exception is
``uncertain_count`` in :class:`ProductionSummaryDTO`, which counts how many already-recorded
channel verdicts were ``RawVerdict.UNCERTAIN`` -- a filter, not a recalculation.

Pydantic models (not the internal dataclasses) are used here specifically so FastAPI can
validate/serialize responses and generate the OpenAPI docs referenced by section 10's
"document: endpoint, request, response" requirement for free.
"""

from __future__ import annotations

from pydantic import BaseModel

from msfc.analytics import HealthState, MachineHealthSnapshot, MachineStatus
from msfc.domain import RawVerdict
from msfc.services import CellSnapshot, DashboardEvent, ProductCycleTrace, RuntimeState


# --------------------------------------------------------------------------- shared/system
class SystemStatusDTO(BaseModel):
    mode: str  # always "SIMULATION" this phase -- section 4.8/15: never claim real hardware
    cell_id: str
    cell_device_id: str
    edge_device_id: str
    line_id: str
    runtime_state: str
    machine_state: str | None
    contract_version: str
    mono_ms: int


def system_status_from_snapshot(snap: CellSnapshot, *, contract_version: str) -> SystemStatusDTO:
    return SystemStatusDTO(
        mode="SIMULATION", cell_id=snap.identity.cell_id, cell_device_id=snap.identity.cell_device_id,
        edge_device_id=snap.identity.edge_device_id, line_id=snap.identity.line_id,
        runtime_state=snap.runtime_state.value,
        machine_state=snap.machine_state.value if snap.machine_state else None,
        contract_version=contract_version, mono_ms=snap.mono_ms,
    )


# --------------------------------------------------------------------------- production
class ProductRecordDTO(BaseModel):
    product_id: str
    detected_at_mono_ms: int
    decided_at_mono_ms: int
    outcome: str
    vision_verdict: str | None
    vision_confidence: float | None
    ocr_verdict: str | None
    ocr_confidence: float | None
    controller_action: str | None
    controller_reason: str | None
    denial_reason: str | None


def product_record_from_trace(trace: ProductCycleTrace) -> ProductRecordDTO:
    return ProductRecordDTO(
        product_id=trace.product_id, detected_at_mono_ms=trace.detected_at_mono_ms,
        decided_at_mono_ms=trace.decided_at_mono_ms, outcome=trace.outcome.value,
        vision_verdict=trace.inspection.verdict.value if trace.inspection else None,
        vision_confidence=trace.inspection.confidence if trace.inspection else None,
        ocr_verdict=trace.label.verdict.value if trace.label else None,
        ocr_confidence=trace.label.confidence if trace.label else None,
        controller_action=trace.sorted_event.action.value if trace.sorted_event else None,
        controller_reason=trace.sorted_event.reason.value if trace.sorted_event else None,
        denial_reason=trace.denial_reason,
    )


class ProductionSummaryDTO(BaseModel):
    total: int
    good: int
    defect: int
    uncertain_count: int
    passed: int
    rejected: int
    session_name: str | None
    latest: ProductRecordDTO | None
    history: list[ProductRecordDTO]


def _is_uncertain(trace: ProductCycleTrace) -> bool:
    channels = [c for c in (trace.inspection, trace.label) if c is not None]
    return any(c.verdict is RawVerdict.UNCERTAIN for c in channels)


def production_summary_from_history(
    history: tuple[ProductCycleTrace, ...], *, session_name: str | None, filter_: str = "all",
) -> ProductionSummaryDTO:
    records = [product_record_from_trace(t) for t in history]
    good = sum(1 for t in history if t.outcome.value == "GOOD")
    defect = sum(1 for t in history if t.outcome.value == "DEFECT")
    uncertain = sum(1 for t in history if _is_uncertain(t))
    passed = sum(1 for r in records if r.controller_action == "PASSED")
    rejected = sum(1 for r in records if r.controller_action == "REJECTED")

    if filter_ == "uncertain":
        records = [r for r in records if r.vision_verdict == "UNCERTAIN" or r.ocr_verdict == "UNCERTAIN"]
    elif filter_ != "all":
        wanted = filter_.upper()
        records = [r for r in records if r.outcome == wanted or r.controller_action == wanted]

    return ProductionSummaryDTO(
        total=len(history), good=good, defect=defect, uncertain_count=uncertain, passed=passed,
        rejected=rejected, session_name=session_name,
        latest=product_record_from_trace(history[-1]) if history else None, history=list(reversed(records)),
    )


# --------------------------------------------------------------------------- vision/ocr/decision pipeline
class PipelineStageDTO(BaseModel):
    stage: str  # "vision" | "ocr" | "decision" | "safety"
    available: bool
    verdict: str | None = None
    confidence: float | None = None
    reason_codes: list[str] = []
    model_name: str | None = None


class VisionOcrPipelineDTO(BaseModel):
    product_id: str | None
    outcome: str | None
    stages: list[PipelineStageDTO]


def vision_ocr_pipeline_from_trace(trace: ProductCycleTrace | None) -> VisionOcrPipelineDTO:
    if trace is None:
        return VisionOcrPipelineDTO(product_id=None, outcome=None, stages=[
            PipelineStageDTO(stage=s, available=False) for s in ("vision", "ocr", "decision", "safety")
        ])
    stages = [
        PipelineStageDTO(stage="vision", available=trace.inspection is not None,
                          verdict=trace.inspection.verdict.value if trace.inspection else None,
                          confidence=trace.inspection.confidence if trace.inspection else None,
                          model_name=trace.inspection.model.name if trace.inspection else None),
        PipelineStageDTO(stage="ocr", available=trace.label is not None,
                          verdict=trace.label.verdict.value if trace.label else None,
                          confidence=trace.label.confidence if trace.label else None,
                          model_name=trace.label.model.name if trace.label else None),
        PipelineStageDTO(stage="decision", available=trace.decision is not None,
                          verdict=trace.decision.final_verdict.value if trace.decision else trace.outcome.value,
                          reason_codes=list(trace.decision.reason_codes) if trace.decision else []),
        PipelineStageDTO(stage="safety", available=trace.outcome.value != "SAFETY_DENIED",
                          verdict="ALLOWED" if trace.outcome.value != "SAFETY_DENIED" else "DENIED",
                          reason_codes=[trace.denial_reason] if trace.denial_reason else []),
    ]
    return VisionOcrPipelineDTO(product_id=trace.product_id, outcome=trace.outcome.value, stages=stages)


# --------------------------------------------------------------------------- safety
class SafetyStatusDTO(BaseModel):
    safety_level: str  # SAFE | WARNING | FAULT | ESTOP | SAFE_STOP | UNKNOWN
    machine_state: str | None
    runtime_state: str
    safety_relay_closed: bool | None
    pusher_state: str | None
    safety_vision_required: bool | None
    active_faults: list[str]
    queue_len: int | None


_SAFETY_LEVEL_BY_MACHINE_STATE = {
    "ESTOP": "ESTOP", "FAULT": "FAULT", "SAFE_STOP": "SAFE_STOP",
}


def safety_status_from_snapshot(snap: CellSnapshot) -> SafetyStatusDTO:
    machine_state = snap.machine_state.value if snap.machine_state else None
    if machine_state is None:
        level = "UNKNOWN"
    elif snap.active_fault_codes and machine_state not in _SAFETY_LEVEL_BY_MACHINE_STATE:
        level = "WARNING"
    else:
        level = _SAFETY_LEVEL_BY_MACHINE_STATE.get(machine_state, "SAFE")
    cell_state = snap.cell_state
    return SafetyStatusDTO(
        safety_level=level, machine_state=machine_state, runtime_state=snap.runtime_state.value,
        safety_relay_closed=cell_state.safety_relay_closed if cell_state else None,
        pusher_state=cell_state.pusher.value if cell_state else None,
        safety_vision_required=cell_state.safety_vision_required if cell_state else None,
        active_faults=list(snap.active_fault_codes), queue_len=cell_state.queue_len if cell_state else None,
    )


# --------------------------------------------------------------------------- machine health
class AnomalyDTO(BaseModel):
    sensor_id: str
    sensor_type: str
    severity: str
    kind: str
    reason: str
    value: float | None
    threshold: float | None


class SensorReadingDTO(BaseModel):
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    quality: str


class HealthStatusDTO(BaseModel):
    configured: bool
    health_state: str
    health_score: float | None
    active_anomalies: list[AnomalyDTO]
    latest_readings: list[SensorReadingDTO]


def health_status_from_snapshot(snap: MachineHealthSnapshot | None) -> HealthStatusDTO:
    if snap is None:
        # Backend not configured -- UNKNOWN, never silently HEALTHY (dashboard section 4.5/11).
        return HealthStatusDTO(configured=False, health_state=HealthState.UNKNOWN.value, health_score=None,
                                active_anomalies=[], latest_readings=[])
    return HealthStatusDTO(
        configured=True, health_state=snap.health_state.value, health_score=snap.health_score.value,
        active_anomalies=[
            AnomalyDTO(sensor_id=a.sensor_id, sensor_type=a.sensor_type.value, severity=a.severity.value,
                       kind=a.kind, reason=a.reason, value=a.value, threshold=a.threshold)
            for a in snap.active_anomalies
        ],
        latest_readings=[
            SensorReadingDTO(sensor_id=m.sensor_id, sensor_type=m.sensor_type.value, value=m.value, unit=m.unit,
                              quality=m.quality.value)
            for m in snap.latest_measurements.values()
        ],
    )


# --------------------------------------------------------------------------- OEE
class OeeStatusDTO(BaseModel):
    configured: bool
    availability: float | None
    performance: float | None
    quality: float | None
    oee: float | None
    total_count: int | None
    good_count: int | None
    defect_count: int | None
    downtime_ms: int | None
    machine_state: str | None
    current_fault: str | None
    cycle_count: int | None
    average_cycle_ms: float | None


def oee_status_from_machine_status(status: MachineStatus | None) -> OeeStatusDTO:
    if status is None:
        return OeeStatusDTO(configured=False, availability=None, performance=None, quality=None, oee=None,
                             total_count=None, good_count=None, defect_count=None, downtime_ms=None,
                             machine_state=None, current_fault=None, cycle_count=None, average_cycle_ms=None)
    oee = status.oee
    return OeeStatusDTO(
        configured=True,
        availability=oee.availability if oee else None, performance=oee.performance if oee else None,
        quality=oee.quality if oee else None, oee=oee.oee if oee else None,
        total_count=oee.total_count if oee else None, good_count=status.good_count,
        defect_count=status.defect_count, downtime_ms=status.downtime_ms,
        machine_state=status.state.value, current_fault=status.current_fault,
        cycle_count=status.cycle_stats.count if status.cycle_stats else None,
        average_cycle_ms=status.cycle_stats.average_ms if status.cycle_stats else None,
    )


# --------------------------------------------------------------------------- events
class EventDTO(BaseModel):
    mono_ms: int
    category: str
    severity: str
    product_id: str | None
    message: str


def event_dto_from_event(event: DashboardEvent) -> EventDTO:
    return EventDTO(mono_ms=event.mono_ms, category=event.category.value, severity=event.severity.value,
                     product_id=event.product_id, message=event.message)


# --------------------------------------------------------------------------- diagnostics
class DiagnosticsDTO(BaseModel):
    mode: str
    runtime_state: str
    machine_state: str | None
    degraded_subsystems: list[str]
    degraded_reasons: dict[str, str]
    active_fault_codes: list[str]
    contract_version: str
    cell_id: str
    cell_device_id: str
    edge_device_id: str


def diagnostics_from_snapshot(snap: CellSnapshot, *, contract_version: str) -> DiagnosticsDTO:
    return DiagnosticsDTO(
        mode="SIMULATION", runtime_state=snap.runtime_state.value,
        machine_state=snap.machine_state.value if snap.machine_state else None,
        degraded_subsystems=list(snap.subsystems.degraded),
        degraded_reasons=dict(zip(snap.subsystems.degraded, snap.subsystems.reasons)),
        active_fault_codes=list(snap.active_fault_codes), contract_version=contract_version,
        cell_id=snap.identity.cell_id, cell_device_id=snap.identity.cell_device_id,
        edge_device_id=snap.identity.edge_device_id,
    )


# --------------------------------------------------------------------------- overview (aggregate of the above)
class OverviewDTO(BaseModel):
    system: SystemStatusDTO
    production: ProductionSummaryDTO
    pipeline: VisionOcrPipelineDTO
    safety: SafetyStatusDTO
    health: HealthStatusDTO
    oee: OeeStatusDTO
    latest_events: list[EventDTO]


# --------------------------------------------------------------------------- control endpoints
class ControlResponseDTO(BaseModel):
    ok: bool
    message: str
    runtime_state: str
    machine_state: str | None


class FullDemoSummaryDTO(BaseModel):
    products_processed: int
    good: int
    defect: int
    rejected: int
    oee: OeeStatusDTO
    health_state: str
    safety_events: list[str]
    faults: list[str]
    final_machine_state: str | None
    final_runtime_state: str
    label: str = "SOFTWARE SIMULATION -- NO PHYSICAL HARDWARE"


def full_demo_summary(
    *, history: list[ProductCycleTrace], oee_status: OeeStatusDTO, health_state: str,
    events: list[DashboardEvent], final_machine_state: str | None, final_runtime_state: str,
) -> FullDemoSummaryDTO:
    good = sum(1 for t in history if t.outcome.value == "GOOD")
    defect = sum(1 for t in history if t.outcome.value == "DEFECT")
    rejected = sum(1 for t in history if t.sorted_event is not None and t.sorted_event.action.value == "REJECTED")
    safety_events = [e.message for e in events if e.category.value == "state"
                     and e.severity.value in ("WARNING", "CRITICAL")]
    faults = [e.message for e in events if e.category.value == "fault"]
    return FullDemoSummaryDTO(
        products_processed=len(history), good=good, defect=defect, rejected=rejected, oee=oee_status,
        health_state=health_state, safety_events=safety_events, faults=faults,
        final_machine_state=final_machine_state, final_runtime_state=final_runtime_state,
    )


__all__ = [
    "SystemStatusDTO", "system_status_from_snapshot",
    "ProductRecordDTO", "product_record_from_trace",
    "ProductionSummaryDTO", "production_summary_from_history",
    "PipelineStageDTO", "VisionOcrPipelineDTO", "vision_ocr_pipeline_from_trace",
    "SafetyStatusDTO", "safety_status_from_snapshot",
    "AnomalyDTO", "SensorReadingDTO", "HealthStatusDTO", "health_status_from_snapshot",
    "OeeStatusDTO", "oee_status_from_machine_status",
    "EventDTO", "event_dto_from_event",
    "DiagnosticsDTO", "diagnostics_from_snapshot",
    "OverviewDTO",
    "ControlResponseDTO", "FullDemoSummaryDTO", "full_demo_summary",
]
