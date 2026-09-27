"""P6.16: ONE full-stack integration test exercising every layer at once:

    Input (synthetic frame) -> Vision -> OCR -> Decision -> Safety Gate -> Cell Command
        -> Controller (real, unmodified msfc.sim.SimCellController)
        -> Event (product_sorted/state_changed/fault, over a real InMemoryBus)
        -> Health/OEE observation (msfc.analytics.MachineHealthMonitor + MachineMonitor)
        -> Transport (the real InMemoryBus/contract registry -- the "Mock Transport" P6.7 asks
           for; msfc.comm.MqttBus, untouched, is the real-broker implementation of the exact
           same MessageBus interface, so nothing here would need to change to run over it)

Distinct from tests/integration/test_services_scenarios.py's 20 narrow, single-purpose
scenarios: this file proves the SUCCESS PATH and the FAILURE PATH each hold across the WHOLE
stack simultaneously, wired once, exactly like the PO's P6.16 diagram.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest

from msfc.analytics import (
    AnomalyThresholds,
    FixedSequenceSensorSource,
    HealthBaseline,
    MachineHealthMonitor,
    MachineMonitor,
    ProductionSession,
    SensorMeasurement,
    SensorType,
    SessionConfig,
)
from msfc.comm import InMemoryBus
from msfc.contracts import ContractRegistry, PayloadValidator
from msfc.decision import DecisionEngine, DecisionPolicy
from msfc.domain import CommandAction, ControlCommand, MachineState
from msfc.domain import ModelInfo
from msfc.ocr import FixtureOcrEngine, LabelValidationConfig, OcrOutput, PreprocessConfig
from msfc.services import CellIdentity, CellRuntime, RuntimeState
from msfc.services.pipeline import OcrStageConfig, VisionStageConfig
from msfc.sim import SimCellController
from msfc.vision import Frame, InferenceOutput, RoiConfig, Thresholds

ROI = RoiConfig(x=0, y=0, width=16, height=16, target_size=(16, 16))
MODEL = ModelInfo(name="full-stack-vision", version="1")
THRESHOLDS = Thresholds(defect_at=0.5, uncertain_band=0.05)
REFERENCE_DATE = date(2026, 1, 1)


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


class _LabelAwareVisionEngine:
    name, version = "full-stack-vision", "1"

    def __init__(self) -> None:
        self._score = 0.02

    def set_score(self, score: float) -> None:
        self._score = score

    def predict(self, image: np.ndarray) -> InferenceOutput:
        return InferenceOutput(class_scores={"GOOD": 1 - self._score, "DEFECT": self._score}, timings_ms={"inference": 0.1})


class _CrashingVisionEngine:
    name, version = "crashing-vision", "1"

    def predict(self, image: np.ndarray) -> InferenceOutput:
        raise RuntimeError("model backend crashed")


class _AlwaysFrameSource:
    def __init__(self) -> None:
        self.closed = False

    def read(self) -> Frame | None:
        return Frame(image=np.zeros((16, 16, 3), dtype=np.uint8), seq=0, captured_mono_ms=0, source="full-stack")

    def close(self) -> None:
        self.closed = True


def _build_stack(registry: ContractRegistry, *, vision_engine, sensor=None) -> dict:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry, heartbeat_timeout_ms=1000)
    identity = CellIdentity(cell_id="cell01", cell_device_id=sim.device_id, edge_device_id="edge01", line_id=sim.line_id)

    ocr_engine = FixtureOcrEngine()
    ocr_engine.set_next_output(OcrOutput(raw_text="EXP 2026-06-01", confidence=0.95))
    ocr = OcrStageConfig(engine=ocr_engine, preprocess=PreprocessConfig(roi=None, target_size=(64, 32)),
                          label_config=LabelValidationConfig(min_confidence=0.5), reference_date=REFERENCE_DATE)

    health_monitor = MachineHealthMonitor(
        baselines={"temp-1": HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=20.0, expected_max=40.0)},
        thresholds={"temp-1": AnomalyThresholds(warning_deviation=2.0, anomaly_deviation=5.0, critical_deviation=10.0)},
        window_ms=5000,
    )
    machine_monitor = MachineMonitor(ProductionSession(
        SessionConfig(planned_production_time_ms=600_000, ideal_cycle_time_ms=1000), started_at_mono_ms=0,
    ))

    runtime = CellRuntime(
        identity=identity, bus=bus, registry=registry,
        decision_engine=DecisionEngine(DecisionPolicy(deadline_ms=300)),
        vision=VisionStageConfig(engine=vision_engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
        frame_source=_AlwaysFrameSource(), ocr=ocr,
        machine_monitor=machine_monitor, health_monitor=health_monitor,
        bridge_health_critical_to_oee=True, sensors=[sensor] if sensor is not None else [],
    )
    runtime.start()
    return {"bus": bus, "sim": sim, "runtime": runtime, "machine_monitor": machine_monitor,
            "health_monitor": health_monitor}


def test_full_stack_success_path(registry: ContractRegistry) -> None:
    """Every layer, one clean GOOD product: vision GOOD + OCR OK -> DecisionEngine GOOD ->
    safety gate allows -> verdict published over the real bus -> the real SimCellController
    accepts it and sorts PASSED -> the resulting events feed OEE -> a healthy sensor reading
    keeps machine health HEALTHY -> every message on the bus validates against its schema."""
    vision_engine = _LabelAwareVisionEngine()
    healthy_sensor = FixedSequenceSensorSource(
        sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE,
        measurements=[SensorMeasurement(sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE, mono_ms=0,
                                         value=25.0, unit="")],
    )
    stack = _build_stack(registry, vision_engine=vision_engine, sensor=healthy_sensor)
    bus, sim, runtime = stack["bus"], stack["sim"], stack["runtime"]

    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="test"), now_mono_ms=0)
    assert runtime.runtime_state is RuntimeState.RUNNING

    runtime.process_sensors(mono_ms=0)
    assert stack["health_monitor"].snapshot(mono_ms=0).health_state.value == "HEALTHY"

    vision_engine.set_score(0.02)
    product_id = sim.detect_product(10)
    trace = runtime.snapshot(mono_ms=10).last_product
    assert trace.product_id == product_id
    assert trace.outcome.value == "GOOD"
    assert trace.inspection is not None and trace.label is not None  # both channels ran

    sim.tick(510)
    sim.receive_edge_heartbeat()
    sorted_event = sim.arrive_at_s2(510)
    assert sorted_event.action.value == "PASSED"

    status = stack["machine_monitor"].status(now_mono_ms=510)
    assert status.good_count == 1 and status.defect_count == 0
    assert status.current_fault is None

    runtime.send_heartbeat(now_mono_ms=510, uptime_ms=510)

    validator = PayloadValidator(registry)
    for message in bus.published:
        match = registry.match_topic(message.topic)
        assert match is not None, f"unregistered topic: {message.topic}"
        spec, _ = match
        validator.validate_for_topic(spec.key, message.envelope)


def test_full_stack_failure_path(registry: ContractRegistry) -> None:
    """Every layer, but everything that can go wrong for one product does: vision crashes,
    a sensor is over-range (health CRITICAL, bridged into OEE as an observational fault but
    NOT gating production), and -- the dominant failure -- an E-stop is pressed before the next
    product is even detected, so the safety gate must deny it outright before OCR/vision/
    decision run at all."""
    critical_sensor = FixedSequenceSensorSource(
        sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE,
        measurements=[SensorMeasurement(sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE, mono_ms=0,
                                         value=55.0, unit="")],
    )
    stack = _build_stack(registry, vision_engine=_CrashingVisionEngine(), sensor=critical_sensor)
    bus, sim, runtime = stack["bus"], stack["sim"], stack["runtime"]

    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="test"), now_mono_ms=0)

    runtime.process_sensors(mono_ms=0)
    assert stack["health_monitor"].snapshot(mono_ms=0).health_state.value == "CRITICAL"

    # Vision is broken, but OCR still works -> a real decision is still reached (GOOD, from OCR alone).
    product_id_1 = sim.detect_product(10)
    trace_1 = runtime.snapshot(mono_ms=10).last_product
    assert trace_1.product_id == product_id_1
    assert trace_1.inspection is None  # vision failed
    assert trace_1.label is not None  # OCR alone carried the decision
    assert trace_1.outcome.value == "GOOD"
    assert runtime.runtime_state is RuntimeState.DEGRADED  # vision is unavailable, but production continues

    sim.tick(520)
    sim.receive_edge_heartbeat()
    sorted_1 = sim.arrive_at_s2(520)
    assert sorted_1.action.value == "PASSED"

    status = stack["machine_monitor"].status(now_mono_ms=520)
    assert status.current_fault == "F070"  # the health CRITICAL bridge, observational only
    assert status.good_count == 1  # health CRITICAL never blocked the product above

    # Now the dominant failure: E-stop. Safety must win over everything else, with no vision/
    # OCR/decision even attempted for the next product.
    sim.press_estop(now_mono_ms=600)
    assert runtime.runtime_state is RuntimeState.SAFE_STOP

    product_id_2 = sim.detect_product(650)
    trace_2 = runtime.snapshot(mono_ms=650).last_product
    assert trace_2.product_id == product_id_2
    assert trace_2.outcome.value == "SAFETY_DENIED"
    assert trace_2.inspection is None and trace_2.label is None and trace_2.decision is None
    assert trace_2.verdict_command is None

    verdict_topic_suffix = "/cmd/verdict"
    verdicts_for_2 = [m for m in bus.published if m.topic.endswith(verdict_topic_suffix)]
    # Exactly one verdict was ever published across this whole test: product 1's. Product 2
    # (post-ESTOP) must never get one.
    assert len(verdicts_for_2) == 1
