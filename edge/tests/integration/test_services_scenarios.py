"""P6.14: 20 deterministic end-to-end scenarios for the Edge AI Cell Platform.

Every scenario wires a REAL (unmodified) msfc.sim.SimCellController to a REAL msfc.services
CellRuntime over a REAL InMemoryBus with the REAL contract registry -- proving the platform
works as a whole, not just that its pieces work in isolation (which the unit tests under
tests/unit/test_services_*.py already cover individually). No randomness anywhere: every
engine/sensor here is a deterministic stub driven by an explicit label/value, matching the
existing pattern in tests/integration/test_full_pipeline_mvp.py and
tests/unit/test_analytics_health_fixtures.py.
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
from msfc.contracts import ContractRegistry
from msfc.decision import DecisionEngine, DecisionPolicy
from msfc.domain import CommandAction, ControlCommand, MachineState, ModelInfo
from msfc.ocr import FixtureOcrEngine, LabelValidationConfig, OcrOutput, PreprocessConfig
from msfc.services import CellIdentity, CellRuntime, RuntimeState
from msfc.services.pipeline import OcrStageConfig, VisionStageConfig
from msfc.sim import SimCellController
from msfc.vision import Frame, InferenceOutput, RoiConfig, Thresholds

ROI = RoiConfig(x=0, y=0, width=16, height=16, target_size=(16, 16))
MODEL = ModelInfo(name="scenario-vision", version="1")
THRESHOLDS = Thresholds(defect_at=0.5, uncertain_band=0.05)
REFERENCE_DATE = date(2026, 1, 1)


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


class _LabelAwareVisionEngine:
    """Deterministic, label-aware stand-in -- same pattern as
    tests/integration/test_full_pipeline_mvp.py's _OracleVisionEngine."""

    name, version = "scenario-vision", "1"

    def __init__(self) -> None:
        self._score: float = 0.02

    def set_score(self, score: float) -> None:
        self._score = score

    def predict(self, image: np.ndarray) -> InferenceOutput:
        return InferenceOutput(class_scores={"GOOD": 1 - self._score, "DEFECT": self._score}, timings_ms={"inference": 0.1})


class _CrashingVisionEngine:
    name, version = "crashing-vision", "1"

    def predict(self, image: np.ndarray) -> InferenceOutput:
        raise RuntimeError("model backend crashed")


class _TimeoutVisionEngine:
    """Models a subsystem timeout (P6.10/P6.14 scenario 19) as an exception -- no real
    async/timeout machinery exists in this synchronous host pipeline, and none is added just
    for this test (P6: no unnecessary new dependencies)."""

    name, version = "timeout-vision", "1"

    def predict(self, image: np.ndarray) -> InferenceOutput:
        raise TimeoutError("vision inference exceeded its deadline")


class _CrashingSensorSource:
    """Models a sensor that cannot be read this tick (P6.10's "sensor unavailable" case) --
    never returns a fabricated value."""

    sensor_id = "temp-1"
    sensor_type = SensorType.TEMPERATURE

    def read(self, *, mono_ms: int) -> SensorMeasurement:
        raise RuntimeError("sensor read failed")


class _AlwaysFrameSource:
    def __init__(self) -> None:
        self.closed = False

    def read(self) -> Frame | None:
        return Frame(image=np.zeros((16, 16, 3), dtype=np.uint8), seq=0, captured_mono_ms=0, source="scenario")

    def close(self) -> None:
        self.closed = True


def _ocr_stage(text: str, confidence: float = 0.95) -> tuple[OcrStageConfig, FixtureOcrEngine]:
    engine = FixtureOcrEngine()
    engine.set_next_output(OcrOutput(raw_text=text, confidence=confidence))
    config = OcrStageConfig(engine=engine, preprocess=PreprocessConfig(roi=None, target_size=(64, 32)),
                             label_config=LabelValidationConfig(min_confidence=0.5), reference_date=REFERENCE_DATE)
    return config, engine


def _health_monitor() -> MachineHealthMonitor:
    return MachineHealthMonitor(
        baselines={"temp-1": HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=20.0, expected_max=40.0)},
        thresholds={"temp-1": AnomalyThresholds(warning_deviation=2.0, anomaly_deviation=5.0, critical_deviation=10.0)},
        window_ms=5000,
    )


def _machine_monitor() -> MachineMonitor:
    session = SessionConfig(planned_production_time_ms=600_000, ideal_cycle_time_ms=1000)
    return MachineMonitor(ProductionSession(session, started_at_mono_ms=0))


class _Rig:
    """One SimCellController + CellRuntime pair on a shared bus, started and RUNNING."""

    def __init__(self, registry: ContractRegistry, **runtime_kwargs) -> None:
        self.bus = InMemoryBus()
        self.sim = SimCellController(bus=self.bus, registry=registry, heartbeat_timeout_ms=1000)
        identity = CellIdentity(cell_id="cell01", cell_device_id=self.sim.device_id, edge_device_id="edge01",
                                 line_id=self.sim.line_id)
        runtime_kwargs.setdefault("decision_engine", DecisionEngine(DecisionPolicy(deadline_ms=300)))
        self.runtime = CellRuntime(identity=identity, bus=self.bus, registry=registry, **runtime_kwargs)
        self.runtime.start()

    def go_running(self, now_mono_ms: int = 0) -> None:
        self.sim.receive_edge_heartbeat()
        self.sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="scenario"),
                               now_mono_ms=now_mono_ms)

    def run_one_cycle(self, t_detect: int, *, travel_ms: int = 500):
        product_id = self.sim.detect_product(t_detect)
        t_s2 = t_detect + travel_ms
        self.sim.tick(t_s2)
        self.sim.receive_edge_heartbeat()
        sorted_event = self.sim.arrive_at_s2(t_s2)
        return product_id, sorted_event


# ------------------------------------------------------------------ 1. GOOD product
def test_scenario_01_good_product(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource())
    rig.go_running()
    engine.set_score(0.02)
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "PASSED"


# ------------------------------------------------------------------ 2. DEFECT product
def test_scenario_02_defect_product(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource())
    rig.go_running()
    engine.set_score(0.98)
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "REJECTED"
    assert sorted_event.reason.value == "VERDICT_DEFECT"


# ------------------------------------------------------------------ 3. UNCERTAIN vision resolves to DEFECT (fail-closed default policy)
def test_scenario_03_uncertain_vision_resolves_to_defect(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource())
    rig.go_running()
    engine.set_score(0.5)  # dead center of the uncertain band
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "REJECTED"


# ------------------------------------------------------------------ 4. OCR valid
def test_scenario_04_ocr_valid_label(registry: ContractRegistry) -> None:
    ocr_config, _ = _ocr_stage("EXP 2026-06-01")
    rig = _Rig(registry, ocr=ocr_config, frame_source=_AlwaysFrameSource())
    rig.go_running()
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "PASSED"


# ------------------------------------------------------------------ 5. OCR invalid (expired label)
def test_scenario_05_ocr_invalid_label(registry: ContractRegistry) -> None:
    ocr_config, _ = _ocr_stage("EXP 2020-01-01")
    rig = _Rig(registry, ocr=ocr_config, frame_source=_AlwaysFrameSource())
    rig.go_running()
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "REJECTED"


# ------------------------------------------------------------------ 6. OCR unavailable (engine misconfigured -> OcrError -> missing channel)
def test_scenario_06_ocr_unavailable_falls_back_to_no_decision(registry: ContractRegistry) -> None:
    bad_config = OcrStageConfig(
        engine=FixtureOcrEngine(),  # never had set_next_output() called -> raises RuntimeError, not OcrError...
        preprocess=PreprocessConfig(roi=None, target_size=(0, 0)),  # ...so force a real OcrError via bad target_size
        label_config=LabelValidationConfig(), reference_date=REFERENCE_DATE,
    )
    rig = _Rig(registry, ocr=bad_config, frame_source=_AlwaysFrameSource())
    rig.go_running()
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "REJECTED"
    assert sorted_event.reason.value == "NO_DECISION"


# ------------------------------------------------------------------ 7. Vision unavailable (engine crash)
def test_scenario_07_vision_unavailable(registry: ContractRegistry) -> None:
    rig = _Rig(registry, vision=VisionStageConfig(engine=_CrashingVisionEngine(), roi=ROI, thresholds=THRESHOLDS,
                                                    model=MODEL), frame_source=_AlwaysFrameSource())
    rig.go_running()
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "REJECTED"
    assert sorted_event.reason.value == "NO_DECISION"
    assert rig.runtime.runtime_state is RuntimeState.DEGRADED


# ------------------------------------------------------------------ 8. Safety denial
def test_scenario_08_safety_denial(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource())
    rig.go_running()
    rig.sim.press_estop(now_mono_ms=50)
    assert rig.runtime.runtime_state is RuntimeState.SAFE_STOP

    product_id = rig.sim.detect_product(60)
    trace = rig.runtime.snapshot(mono_ms=60).last_product
    assert trace.product_id == product_id
    assert trace.outcome.value == "SAFETY_DENIED"
    assert trace.verdict_command is None


# ------------------------------------------------------------------ 9. Communication loss
def test_scenario_09_communication_loss(registry: ContractRegistry) -> None:
    rig = _Rig(registry)
    rig.go_running()
    rig.sim.tick(2000)  # no more receive_edge_heartbeat() calls -> heartbeat_timeout_ms=1000 exceeded
    assert rig.sim.state is MachineState.FAULT
    assert rig.runtime.runtime_state is RuntimeState.SAFE_STOP  # FAULT is a latched state


# ------------------------------------------------------------------ 10. Machine-health WARNING
def test_scenario_10_health_warning(registry: ContractRegistry) -> None:
    monitor = _health_monitor()
    rig = _Rig(registry, health_monitor=monitor, sensors=[])
    rig.go_running()
    measurement = SensorMeasurement(sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=42.5, unit="")
    monitor.ingest(measurement, mono_ms=0)
    assert monitor.snapshot(mono_ms=0).health_state.value == "WARNING"


# ------------------------------------------------------------------ 11. Machine-health ANOMALY
def test_scenario_11_health_anomaly(registry: ContractRegistry) -> None:
    monitor = _health_monitor()
    rig = _Rig(registry, health_monitor=monitor, sensors=[])
    rig.go_running()
    monitor.ingest(SensorMeasurement(sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=46.0, unit=""),
                    mono_ms=0)
    assert monitor.snapshot(mono_ms=0).health_state.value == "ANOMALY"


# ------------------------------------------------------------------ 12. Machine-health CRITICAL, bridged to OEE, production continues
def test_scenario_12_health_critical_bridged_but_does_not_block_production(registry: ContractRegistry) -> None:
    monitor = _health_monitor()
    machine_monitor = _machine_monitor()
    engine = _LabelAwareVisionEngine()
    critical_sensor = FixedSequenceSensorSource(
        sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE,
        measurements=[SensorMeasurement(sensor_id="temp-1", sensor_type=SensorType.TEMPERATURE, mono_ms=0,
                                         value=55.0, unit="")],
    )
    rig = _Rig(registry, health_monitor=monitor, machine_monitor=machine_monitor,
               bridge_health_critical_to_oee=True, sensors=[critical_sensor],
               vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource())
    rig.go_running()
    rig.runtime.process_sensors(mono_ms=0)  # reads the sensor, ingests, drains + bridges -- all through the runtime's own entry point

    engine.set_score(0.02)
    _, sorted_event = rig.run_one_cycle(10)
    assert sorted_event.action.value == "PASSED"  # health CRITICAL never gates production (D-054)
    assert machine_monitor.session.status(now_mono_ms=600).current_fault == "F070"


# ------------------------------------------------------------------ 13. Multiple simultaneous faults (vision failing + health critical)
def test_scenario_13_multiple_simultaneous_faults(registry: ContractRegistry) -> None:
    monitor = _health_monitor()
    rig = _Rig(registry, health_monitor=monitor, sensors=[_CrashingSensorSource()],
               vision=VisionStageConfig(engine=_CrashingVisionEngine(), roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource())
    rig.go_running()
    rig.runtime.process_sensors(mono_ms=0)
    rig.sim.detect_product(10)

    snap = rig.runtime.snapshot(mono_ms=10)
    assert set(snap.subsystems.degraded) == {"vision", "health"}


# ------------------------------------------------------------------ 14. Recovery (SAFE_STOP -> READY -> RUNNING)
def test_scenario_14_recovery_after_estop(registry: ContractRegistry) -> None:
    rig = _Rig(registry)
    rig.go_running()
    rig.sim.press_estop(now_mono_ms=50)
    assert rig.runtime.runtime_state is RuntimeState.SAFE_STOP

    rig.sim.release_estop(now_mono_ms=100)
    rig.sim.local_reset(now_mono_ms=100)
    assert rig.runtime.runtime_state is RuntimeState.READY

    rig.go_running(now_mono_ms=100)
    assert rig.runtime.runtime_state is RuntimeState.RUNNING


# ------------------------------------------------------------------ 15. Degraded mode: OEE not configured must not block production
def test_scenario_15_oee_not_configured_does_not_block_production(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource())  # machine_monitor deliberately omitted
    rig.go_running()
    engine.set_score(0.02)
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "PASSED"
    assert rig.runtime.runtime_state is RuntimeState.RUNNING  # never DEGRADED just for an unconfigured subsystem


# ------------------------------------------------------------------ 16. Normal production sequence (several GOOD in a row)
def test_scenario_16_normal_production_sequence(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    machine_monitor = _machine_monitor()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource(), machine_monitor=machine_monitor)
    rig.go_running()
    engine.set_score(0.02)
    t = 0
    for _ in range(4):
        _, sorted_event = rig.run_one_cycle(t)
        assert sorted_event.action.value == "PASSED"
        t += 600
    status = machine_monitor.status(now_mono_ms=t)
    assert status.good_count == 4 and status.defect_count == 0


# ------------------------------------------------------------------ 17. Mixed GOOD/DEFECT batch
def test_scenario_17_mixed_good_defect_batch(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    machine_monitor = _machine_monitor()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource(), machine_monitor=machine_monitor)
    rig.go_running()
    t = 0
    for score in (0.02, 0.98, 0.02, 0.98, 0.98):
        engine.set_score(score)
        rig.run_one_cycle(t)
        t += 600
    status = machine_monitor.status(now_mono_ms=t)
    assert status.good_count == 2 and status.defect_count == 3


# ------------------------------------------------------------------ 18. Malformed event does not crash the runtime
def test_scenario_18_malformed_event_is_dropped_not_crashed(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=_AlwaysFrameSource())
    rig.go_running()

    topic = registry.format_topic("conveyor.event.product_detected", device_id=rig.sim.device_id,
                                   line_id=rig.sim.line_id)
    published_before = len(rig.bus.published)
    rig.bus.publish(topic, {"not": "a valid envelope"})  # no exception should escape
    assert len(rig.bus.published) == published_before + 1  # the malformed message itself was recorded...
    verdicts = [m for m in rig.bus.published if m.topic.endswith("/cmd/verdict")]
    assert verdicts == []  # ...but never turned into a verdict


# ------------------------------------------------------------------ 19. Subsystem timeout
def test_scenario_19_subsystem_timeout(registry: ContractRegistry) -> None:
    rig = _Rig(registry, vision=VisionStageConfig(engine=_TimeoutVisionEngine(), roi=ROI, thresholds=THRESHOLDS,
                                                    model=MODEL), frame_source=_AlwaysFrameSource())
    rig.go_running()
    _, sorted_event = rig.run_one_cycle(0)
    assert sorted_event.action.value == "REJECTED"
    assert sorted_event.reason.value == "NO_DECISION"


# ------------------------------------------------------------------ 20. Full clean shutdown
def test_scenario_20_full_clean_shutdown(registry: ContractRegistry) -> None:
    engine = _LabelAwareVisionEngine()
    frame_source = _AlwaysFrameSource()
    rig = _Rig(registry, vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
               frame_source=frame_source)
    rig.go_running()
    engine.set_score(0.02)
    rig.run_one_cycle(0)

    rig.runtime.shutdown()
    assert rig.runtime.runtime_state is RuntimeState.SHUTDOWN
    assert frame_source.closed is True

    published_before = len(rig.bus.published)
    rig.sim.detect_product(600)
    new_verdicts = [m for m in rig.bus.published[published_before:] if m.topic.endswith("/cmd/verdict")]
    assert new_verdicts == []

    rig.runtime.shutdown()  # idempotent
    assert rig.runtime.runtime_state is RuntimeState.SHUTDOWN
