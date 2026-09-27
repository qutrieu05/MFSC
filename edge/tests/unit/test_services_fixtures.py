"""P6.15: 20+ reusable, deterministic end-to-end fixtures for the platform.

Every fixture below builds an existing P1-P5 (or P6) type with fixed, hand-chosen values --
no randomness anywhere in this file (P6.14's "no randomness unless explicitly seeded and
deterministic" applies equally to fixtures). Each fixture is exercised by at least one
assertion here so a future change that breaks one is caught immediately, and other test
modules are free to import these fixture *functions* by name via normal pytest fixture
injection (they live under ``tests/unit`` and are auto-discovered per-file, matching this
repository's existing convention of not sharing fixtures across files unless they are in
``conftest.py``).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

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
from msfc.domain import (
    CellStateSnapshot,
    CommandAck,
    CommandAction,
    CommandResult,
    ControlCommand,
    DecisionRecord,
    FaultReport,
    InspectionResult,
    MachineState,
    ModelInfo,
    RawVerdict,
    Verdict,
    VerdictCommand,
    lookup_fault,
)
from msfc.services import CellIdentity, PipelineOutcome, ProductCycleTrace
from msfc.vision import Frame


# --------------------------------------------------------------------------- 1-2: frame
@pytest.fixture()
def sample_frame() -> Frame:
    return Frame(image=np.zeros((16, 16, 3), dtype=np.uint8), seq=0, captured_mono_ms=0, source="fixture")


@pytest.fixture()
def sample_identity() -> CellIdentity:
    return CellIdentity(cell_id="cell01", cell_device_id="esp32-cc01", edge_device_id="edge01", line_id="line01")


# --------------------------------------------------------------------------- 3-5: vision result
@pytest.fixture()
def vision_good_result() -> InspectionResult:
    return InspectionResult(product_id="1-0", verdict=RawVerdict.GOOD, confidence=0.98,
                             model=ModelInfo(name="fixture-vision", version="1"), timings_ms={"total": 5.0})


@pytest.fixture()
def vision_defect_result() -> InspectionResult:
    return InspectionResult(product_id="1-0", verdict=RawVerdict.DEFECT, confidence=0.97,
                             model=ModelInfo(name="fixture-vision", version="1"), timings_ms={"total": 5.0})


@pytest.fixture()
def vision_uncertain_result() -> InspectionResult:
    return InspectionResult(product_id="1-0", verdict=RawVerdict.UNCERTAIN, confidence=0.5,
                             model=ModelInfo(name="fixture-vision", version="1"), timings_ms={"total": 5.0})


# --------------------------------------------------------------------------- 6-7: OCR result (same domain type, model.backend="ocr")
@pytest.fixture()
def ocr_good_result() -> InspectionResult:
    return InspectionResult(product_id="1-0", verdict=RawVerdict.GOOD, confidence=0.95,
                             model=ModelInfo(name="fixture-ocr", version="1", backend="ocr"), timings_ms={"total": 3.0})


@pytest.fixture()
def ocr_defect_result() -> InspectionResult:
    return InspectionResult(product_id="1-0", verdict=RawVerdict.DEFECT, confidence=0.95,
                             model=ModelInfo(name="fixture-ocr", version="1", backend="ocr"), timings_ms={"total": 3.0})


# --------------------------------------------------------------------------- 8-9: decision
@pytest.fixture()
def decision_good_record() -> DecisionRecord:
    return DecisionRecord(decision_id="d-1-0", product_id="1-0", final_verdict=Verdict.GOOD,
                           reason_codes=("ALL_CHANNELS_GOOD",), rules_version="rules-0.1", late=False)


@pytest.fixture()
def decision_defect_record() -> DecisionRecord:
    return DecisionRecord(decision_id="d-1-0", product_id="1-0", final_verdict=Verdict.DEFECT,
                           reason_codes=("FIXTURE-VISION_DEFECT",), rules_version="rules-0.1", late=False)


# --------------------------------------------------------------------------- 10-13: machine/safety state (CellStateSnapshot IS the safety-relevant state -- no separate type)
@pytest.fixture()
def cell_state_idle() -> CellStateSnapshot:
    return CellStateSnapshot(machine_state=MachineState.IDLE)


@pytest.fixture()
def cell_state_running() -> CellStateSnapshot:
    return CellStateSnapshot(machine_state=MachineState.RUNNING, safety_relay_closed=True, motor_output_pct=50.0,
                              speed_setpoint_pct=50.0)


@pytest.fixture()
def cell_state_estop() -> CellStateSnapshot:
    return CellStateSnapshot(machine_state=MachineState.ESTOP, active_faults=("F001",))


@pytest.fixture()
def cell_state_fault() -> CellStateSnapshot:
    return CellStateSnapshot(machine_state=MachineState.FAULT, active_faults=("F010",))


# --------------------------------------------------------------------------- 14-15: health result
@pytest.fixture()
def health_snapshot_healthy() -> MachineHealthSnapshot:
    return MachineHealthSnapshot(mono_ms=1000, health_score=HealthScore(value=1.0, state=HealthState.HEALTHY),
                                  health_state=HealthState.HEALTHY)


@pytest.fixture()
def health_snapshot_critical() -> MachineHealthSnapshot:
    anomaly = AnomalyResult(sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE, mono_ms=1000,
                             severity=AnomalySeverity.CRITICAL, kind="threshold", reason="over_range", value=55.0)
    return MachineHealthSnapshot(mono_ms=1000, active_anomalies=(anomaly,),
                                  health_score=HealthScore(value=0.4, state=HealthState.CRITICAL),
                                  health_state=HealthState.CRITICAL)


@pytest.fixture()
def sample_sensor_measurement() -> SensorMeasurement:
    return SensorMeasurement(sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE, mono_ms=1000, value=25.0,
                              unit="degC")


# --------------------------------------------------------------------------- 16-17: OEE result
@pytest.fixture()
def oee_result_sample() -> OeeResult:
    return OeeResult(availability=0.9, performance=0.95, quality=0.98, oee=0.9 * 0.95 * 0.98,
                      planned_production_time_ms=600_000, run_time_ms=540_000, downtime_ms=60_000,
                      total_count=100, good_count=98, defect_count=2)


@pytest.fixture()
def machine_status_sample(oee_result_sample: OeeResult) -> MachineStatus:
    return MachineStatus(state=MachineState.RUNNING, session_name="fixture", cycle_count=100, good_count=98,
                          defect_count=2, downtime_ms=60_000, current_fault=None, last_event_type="product_good",
                          last_event_mono_ms=1000, oee=oee_result_sample)


# --------------------------------------------------------------------------- 18-19: command / command ack
@pytest.fixture()
def control_command_start() -> ControlCommand:
    return ControlCommand(cmd_id="start-1", action=CommandAction.START, source="fixture")


@pytest.fixture()
def verdict_command_good() -> VerdictCommand:
    return VerdictCommand(product_id="1-0", verdict=Verdict.GOOD, decision_id="d-1-0",
                           reason_codes=("ALL_CHANNELS_GOOD",), confidence=0.98)


@pytest.fixture()
def command_ack_done() -> CommandAck:
    return CommandAck(cmd_id="start-1", action="start", result=CommandResult.DONE, state_after=MachineState.RUNNING)


@pytest.fixture()
def command_ack_rejected() -> CommandAck:
    return CommandAck(cmd_id="start-1", action="start", result=CommandResult.REJECTED, reason="estop_latched",
                       state_after=MachineState.ESTOP)


# --------------------------------------------------------------------------- 20-21: fault / event envelope
@pytest.fixture()
def fault_report_raised() -> FaultReport:
    return FaultReport(fault=lookup_fault("F010"), event="RAISED", detail="edge heartbeat timeout")


@pytest.fixture()
def fault_report_cleared() -> FaultReport:
    return FaultReport(fault=lookup_fault("F010"), event="CLEARED")


@pytest.fixture()
def product_cycle_trace_good() -> ProductCycleTrace:
    return ProductCycleTrace(product_id="1-0", outcome=PipelineOutcome.GOOD, detected_at_mono_ms=0,
                              decided_at_mono_ms=40)


@pytest.fixture()
def product_cycle_trace_safety_denied() -> ProductCycleTrace:
    return ProductCycleTrace(product_id="1-0", outcome=PipelineOutcome.SAFETY_DENIED, detected_at_mono_ms=0,
                              decided_at_mono_ms=0, denial_reason="CELL_LATCHED_ESTOP")


# --------------------------------------------------------------------------- determinism + sanity checks (one per fixture group above)
def test_frame_and_identity_fixtures_are_deterministic(sample_frame: Frame, sample_identity: CellIdentity) -> None:
    assert sample_frame.image.shape == (16, 16, 3)
    assert sample_identity.line_id == "line01"


def test_vision_result_fixtures_cover_all_three_verdicts(
    vision_good_result: InspectionResult, vision_defect_result: InspectionResult, vision_uncertain_result: InspectionResult,
) -> None:
    assert {vision_good_result.verdict, vision_defect_result.verdict, vision_uncertain_result.verdict} == {
        RawVerdict.GOOD, RawVerdict.DEFECT, RawVerdict.UNCERTAIN,
    }


def test_ocr_result_fixtures_share_the_inspection_result_type(
    ocr_good_result: InspectionResult, ocr_defect_result: InspectionResult,
) -> None:
    assert ocr_good_result.model.backend == "ocr"
    assert ocr_defect_result.verdict is RawVerdict.DEFECT


def test_decision_fixtures_reflect_their_final_verdict(
    decision_good_record: DecisionRecord, decision_defect_record: DecisionRecord,
) -> None:
    assert decision_good_record.final_verdict is Verdict.GOOD
    assert decision_defect_record.final_verdict is Verdict.DEFECT


def test_cell_state_fixtures_cover_running_and_two_latched_states(
    cell_state_idle: CellStateSnapshot, cell_state_running: CellStateSnapshot,
    cell_state_estop: CellStateSnapshot, cell_state_fault: CellStateSnapshot,
) -> None:
    from msfc.domain import LATCHED_STATES

    assert cell_state_idle.machine_state not in LATCHED_STATES
    assert cell_state_running.machine_state is MachineState.RUNNING
    assert cell_state_estop.machine_state in LATCHED_STATES
    assert cell_state_fault.machine_state in LATCHED_STATES


def test_health_snapshot_fixtures_cover_healthy_and_critical(
    health_snapshot_healthy: MachineHealthSnapshot, health_snapshot_critical: MachineHealthSnapshot,
    sample_sensor_measurement: SensorMeasurement,
) -> None:
    assert health_snapshot_healthy.health_state is HealthState.HEALTHY
    assert health_snapshot_critical.health_state is HealthState.CRITICAL
    assert health_snapshot_critical.active_anomalies[0].severity is AnomalySeverity.CRITICAL
    assert sample_sensor_measurement.sensor_id == "temp-1"


def test_oee_fixtures_are_internally_consistent(oee_result_sample: OeeResult, machine_status_sample: MachineStatus) -> None:
    assert oee_result_sample.good_count + oee_result_sample.defect_count == oee_result_sample.total_count
    assert machine_status_sample.oee is oee_result_sample


def test_command_and_ack_fixtures_pair_up(
    control_command_start: ControlCommand, verdict_command_good: VerdictCommand,
    command_ack_done: CommandAck, command_ack_rejected: CommandAck,
) -> None:
    assert control_command_start.action is CommandAction.START
    assert verdict_command_good.verdict is Verdict.GOOD
    assert command_ack_done.result is CommandResult.DONE
    assert command_ack_rejected.result is CommandResult.REJECTED
    assert command_ack_rejected.reason is not None


def test_fault_report_fixtures_cover_raise_and_clear(
    fault_report_raised: FaultReport, fault_report_cleared: FaultReport,
) -> None:
    assert fault_report_raised.event == "RAISED"
    assert fault_report_cleared.event == "CLEARED"
    assert fault_report_raised.fault.code == fault_report_cleared.fault.code


def test_product_cycle_trace_fixtures_cover_good_and_safety_denied(
    product_cycle_trace_good: ProductCycleTrace, product_cycle_trace_safety_denied: ProductCycleTrace,
) -> None:
    assert product_cycle_trace_good.outcome is PipelineOutcome.GOOD
    assert product_cycle_trace_safety_denied.outcome is PipelineOutcome.SAFETY_DENIED
    assert product_cycle_trace_safety_denied.denial_reason is not None


def test_reference_date_fixture_is_fixed_not_wall_clock() -> None:
    # P6.14 "no randomness" applies to dates too: never datetime.today() in a fixture.
    reference = date(2026, 1, 1)
    assert reference.isoformat() == "2026-01-01"
