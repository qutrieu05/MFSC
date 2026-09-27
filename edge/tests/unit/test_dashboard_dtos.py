"""Dashboard DTO builders: pure functions, tested without any FastAPI/session machinery."""

from __future__ import annotations

from msfc.analytics import (
    AnomalyResult,
    AnomalySeverity,
    HealthScore,
    HealthState,
    MachineHealthSnapshot,
    MachineStatus,
    OeeResult,
    SensorMeasurement,
    SensorType,
)
from msfc.dashboard import dtos
from msfc.domain import InspectionResult, MachineState, ModelInfo, RawVerdict
from msfc.services import CellIdentity, CellSnapshot, PipelineOutcome, ProductCycleTrace, RuntimeState

IDENTITY = CellIdentity(cell_id="c1", cell_device_id="esp32-cc01", edge_device_id="edge01", line_id="line01")


def _vision(verdict: RawVerdict) -> InspectionResult:
    return InspectionResult(product_id="1-0", verdict=verdict, confidence=0.9,
                             model=ModelInfo(name="v", version="1"), timings_ms={"total": 1.0})


def test_health_status_unknown_when_not_configured() -> None:
    dto = dtos.health_status_from_snapshot(None)
    assert dto.configured is False
    assert dto.health_state == "UNKNOWN"  # never silently HEALTHY


def test_health_status_from_real_snapshot() -> None:
    snap = MachineHealthSnapshot(
        mono_ms=100, health_score=HealthScore(value=0.4, state=HealthState.CRITICAL),
        health_state=HealthState.CRITICAL,
        active_anomalies=(AnomalyResult(sensor_id="t1", sensor_type=SensorType.TEMPERATURE, mono_ms=100,
                                         severity=AnomalySeverity.CRITICAL, kind="threshold", reason="x"),),
        latest_measurements={"t1": SensorMeasurement(sensor_id="t1", sensor_type=SensorType.TEMPERATURE,
                                                      mono_ms=100, value=55.0, unit="degC")},
    )
    dto = dtos.health_status_from_snapshot(snap)
    assert dto.configured is True
    assert dto.health_state == "CRITICAL"
    assert len(dto.active_anomalies) == 1
    assert dto.latest_readings[0].value == 55.0


def test_oee_status_not_configured() -> None:
    dto = dtos.oee_status_from_machine_status(None)
    assert dto.configured is False
    assert dto.oee is None


def test_oee_status_copies_numbers_verbatim_not_recomputed() -> None:
    oee = OeeResult(availability=0.9, performance=0.8, quality=0.95, oee=0.684, planned_production_time_ms=1000,
                     run_time_ms=900, downtime_ms=100, total_count=10, good_count=9, defect_count=1)
    status = MachineStatus(state=MachineState.RUNNING, session_name="s", cycle_count=10, good_count=9,
                            defect_count=1, downtime_ms=100, current_fault=None, last_event_type=None,
                            last_event_mono_ms=None, oee=oee)
    dto = dtos.oee_status_from_machine_status(status)
    assert dto.oee == oee.oee  # same object's value, not a UI-side recalculation
    assert dto.availability == oee.availability


def test_vision_ocr_pipeline_distinguishes_all_four_stages() -> None:
    trace = ProductCycleTrace(product_id="1-0", outcome=PipelineOutcome.DEFECT, detected_at_mono_ms=0,
                               decided_at_mono_ms=10, inspection=_vision(RawVerdict.GOOD),
                               label=_vision(RawVerdict.DEFECT))
    dto = dtos.vision_ocr_pipeline_from_trace(trace)
    stages = {s.stage: s for s in dto.stages}
    assert stages["vision"].verdict == "GOOD"
    assert stages["ocr"].verdict == "DEFECT"
    assert stages["safety"].verdict == "ALLOWED"
    assert stages["vision"].verdict != stages["ocr"].verdict  # never collapsed into one value


def test_vision_ocr_pipeline_shows_safety_denied() -> None:
    trace = ProductCycleTrace(product_id="1-0", outcome=PipelineOutcome.SAFETY_DENIED, detected_at_mono_ms=0,
                               decided_at_mono_ms=0, denial_reason="CELL_LATCHED_ESTOP")
    dto = dtos.vision_ocr_pipeline_from_trace(trace)
    safety_stage = next(s for s in dto.stages if s.stage == "safety")
    assert safety_stage.verdict == "DENIED"
    vision_stage = next(s for s in dto.stages if s.stage == "vision")
    assert vision_stage.available is False  # never called -- see module docstring


def test_vision_ocr_pipeline_no_data_yet() -> None:
    dto = dtos.vision_ocr_pipeline_from_trace(None)
    assert dto.product_id is None
    assert all(not s.available for s in dto.stages)


def test_safety_status_estop_is_never_shown_as_safe() -> None:
    snap = CellSnapshot(identity=IDENTITY, runtime_state=RuntimeState.SAFE_STOP, mono_ms=0,
                         machine_state=MachineState.ESTOP, active_fault_codes=("F001",))
    dto = dtos.safety_status_from_snapshot(snap)
    assert dto.safety_level == "ESTOP"


def test_safety_status_unknown_when_no_state_observed_yet() -> None:
    snap = CellSnapshot(identity=IDENTITY, runtime_state=RuntimeState.INIT, mono_ms=0)
    dto = dtos.safety_status_from_snapshot(snap)
    assert dto.safety_level == "UNKNOWN"  # never SAFE just because nothing is known yet


def test_production_summary_counts_uncertain_via_channel_verdicts() -> None:
    good = ProductCycleTrace(product_id="1-0", outcome=PipelineOutcome.GOOD, detected_at_mono_ms=0,
                              decided_at_mono_ms=0, inspection=_vision(RawVerdict.GOOD))
    uncertain = ProductCycleTrace(product_id="1-1", outcome=PipelineOutcome.DEFECT, detected_at_mono_ms=0,
                                   decided_at_mono_ms=0, inspection=_vision(RawVerdict.UNCERTAIN))
    summary = dtos.production_summary_from_history((good, uncertain), session_name="s")
    assert summary.total == 2
    assert summary.uncertain_count == 1


def test_production_summary_filter_uncertain() -> None:
    good = ProductCycleTrace(product_id="1-0", outcome=PipelineOutcome.GOOD, detected_at_mono_ms=0,
                              decided_at_mono_ms=0, inspection=_vision(RawVerdict.GOOD))
    uncertain = ProductCycleTrace(product_id="1-1", outcome=PipelineOutcome.DEFECT, detected_at_mono_ms=0,
                                   decided_at_mono_ms=0, inspection=_vision(RawVerdict.UNCERTAIN))
    summary = dtos.production_summary_from_history((good, uncertain), session_name="s", filter_="uncertain")
    assert len(summary.history) == 1
    assert summary.history[0].product_id == "1-1"
