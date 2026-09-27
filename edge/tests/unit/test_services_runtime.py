"""P6.3: CellRuntime lifecycle tests, wired to a real (unmodified) SimCellController over a
real InMemoryBus -- the same "talk only through the bus" property a real ESP32 would require
(P6.19). Only test files may import msfc.sim (see msfc/services/__init__.py's docstring)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from msfc.comm import InMemoryBus
from msfc.contracts import ContractRegistry
from msfc.decision import DecisionEngine, DecisionPolicy
from msfc.domain import CommandAction, ControlCommand, MachineState, ModelInfo
from msfc.services import CellIdentity, CellRuntime, RuntimeState
from msfc.services.pipeline import VisionStageConfig
from msfc.sim import SimCellController
from msfc.vision import Frame, InferenceOutput, RoiConfig, Thresholds

ROI = RoiConfig(x=0, y=0, width=16, height=16, target_size=(16, 16))
MODEL = ModelInfo(name="stub", version="1")
THRESHOLDS = Thresholds(defect_at=0.5, uncertain_band=0.05)


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


class _GoodEngine:
    name, version = "stub", "1"

    def predict(self, image: np.ndarray) -> InferenceOutput:
        return InferenceOutput(class_scores={"GOOD": 0.98, "DEFECT": 0.02}, timings_ms={"inference": 0.1})


class _CrashingEngine:
    name, version = "crashing", "1"

    def predict(self, image: np.ndarray) -> InferenceOutput:
        raise RuntimeError("model backend crashed")


class _OneShotFrameSource:
    """Returns exactly one frame, then None -- enough to drive one product cycle per test."""

    def __init__(self) -> None:
        self._served = False
        self.closed = False

    def read(self) -> Frame | None:
        if self._served:
            return None
        self._served = True
        return Frame(image=np.zeros((16, 16, 3), dtype=np.uint8), seq=0, captured_mono_ms=0, source="test")

    def close(self) -> None:
        self.closed = True


class _AlwaysFrameSource:
    def __init__(self) -> None:
        self.closed = False

    def read(self) -> Frame | None:
        return Frame(image=np.zeros((16, 16, 3), dtype=np.uint8), seq=0, captured_mono_ms=0, source="test")

    def close(self) -> None:
        self.closed = True


def _identity(sim: SimCellController) -> CellIdentity:
    return CellIdentity(cell_id="cell01", cell_device_id=sim.device_id, edge_device_id="edge01", line_id=sim.line_id)


def test_runtime_is_init_before_start(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    runtime = CellRuntime(identity=_identity(sim), bus=bus, registry=registry,
                           decision_engine=DecisionEngine(DecisionPolicy()))
    assert runtime.runtime_state is RuntimeState.INIT


def test_runtime_becomes_ready_from_retained_state_on_start(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)  # already booted to IDLE, retained state published
    runtime = CellRuntime(identity=_identity(sim), bus=bus, registry=registry,
                           decision_engine=DecisionEngine(DecisionPolicy()))
    runtime.start()
    assert runtime.runtime_state is RuntimeState.READY
    assert runtime.snapshot(mono_ms=0).machine_state is MachineState.IDLE


def test_runtime_tracks_cell_running_and_safe_stop(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    runtime = CellRuntime(identity=_identity(sim), bus=bus, registry=registry,
                           decision_engine=DecisionEngine(DecisionPolicy()))
    runtime.start()

    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="test"), now_mono_ms=0)
    assert runtime.runtime_state is RuntimeState.RUNNING

    sim.press_estop(now_mono_ms=100)
    assert runtime.runtime_state is RuntimeState.SAFE_STOP

    sim.release_estop(now_mono_ms=200)
    sim.local_reset(now_mono_ms=200)
    assert runtime.runtime_state is RuntimeState.READY


def test_runtime_publishes_a_verdict_that_the_real_sim_controller_accepts(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    runtime = CellRuntime(
        identity=_identity(sim), bus=bus, registry=registry,
        decision_engine=DecisionEngine(DecisionPolicy(deadline_ms=300)),
        vision=VisionStageConfig(engine=_GoodEngine(), roi=ROI, thresholds=THRESHOLDS, model=MODEL),
        frame_source=_OneShotFrameSource(),
    )
    runtime.start()
    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="test"), now_mono_ms=0)

    product_id = sim.detect_product(0)
    assert runtime.snapshot(mono_ms=0).last_product is not None
    assert runtime.snapshot(mono_ms=0).last_product.product_id == product_id
    assert runtime.snapshot(mono_ms=0).last_product.outcome.value == "GOOD"

    sim.tick(500)
    sim.receive_edge_heartbeat()
    sorted_event = sim.arrive_at_s2(500)
    assert sorted_event.action.value == "PASSED"  # proves the verdict really reached the real sim controller

    trace = runtime.snapshot(mono_ms=500).last_product
    assert trace.sorted_event is not None
    assert trace.sorted_event.action.value == "PASSED"


def test_runtime_degrades_then_faults_after_repeated_vision_failures(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    runtime = CellRuntime(
        identity=_identity(sim), bus=bus, registry=registry,
        decision_engine=DecisionEngine(DecisionPolicy()),
        vision=VisionStageConfig(engine=_CrashingEngine(), roi=ROI, thresholds=THRESHOLDS, model=MODEL),
        frame_source=_AlwaysFrameSource(), fault_threshold=3,
    )
    runtime.start()
    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="test"), now_mono_ms=0)

    sim.detect_product(0)
    assert runtime.runtime_state is RuntimeState.DEGRADED

    sim.detect_product(10)
    sim.detect_product(20)
    assert runtime.runtime_state is RuntimeState.FAULT


def test_runtime_recovers_from_degraded_after_a_successful_cycle(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    engine = _CrashingEngine()
    runtime = CellRuntime(
        identity=_identity(sim), bus=bus, registry=registry,
        decision_engine=DecisionEngine(DecisionPolicy()),
        vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
        frame_source=_AlwaysFrameSource(),
    )
    runtime.start()
    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="test"), now_mono_ms=0)

    sim.detect_product(0)
    assert runtime.runtime_state is RuntimeState.DEGRADED

    runtime._vision = VisionStageConfig(engine=_GoodEngine(), roi=ROI, thresholds=THRESHOLDS, model=MODEL)
    sim.detect_product(10)
    assert runtime.runtime_state is RuntimeState.RUNNING


def test_shutdown_stops_publishing_new_verdicts(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    runtime = CellRuntime(
        identity=_identity(sim), bus=bus, registry=registry,
        decision_engine=DecisionEngine(DecisionPolicy()),
        vision=VisionStageConfig(engine=_GoodEngine(), roi=ROI, thresholds=THRESHOLDS, model=MODEL),
        frame_source=_AlwaysFrameSource(),
    )
    runtime.start()
    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="test"), now_mono_ms=0)

    frame_source = runtime._frame_source
    runtime.shutdown()
    assert runtime.runtime_state is RuntimeState.SHUTDOWN
    assert frame_source.closed is True

    published_before = len(bus.published)
    sim.detect_product(0)
    verdict_topic_suffix = "/cmd/verdict"
    new_verdicts = [m for m in bus.published[published_before:] if m.topic.endswith(verdict_topic_suffix)]
    assert new_verdicts == []


def test_send_heartbeat_reports_services_ok_false_when_faulted(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    runtime = CellRuntime(
        identity=_identity(sim), bus=bus, registry=registry,
        decision_engine=DecisionEngine(DecisionPolicy()),
        vision=VisionStageConfig(engine=_CrashingEngine(), roi=ROI, thresholds=THRESHOLDS, model=MODEL),
        frame_source=_AlwaysFrameSource(), fault_threshold=1,
    )
    runtime.start()
    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="start-1", action=CommandAction.START, source="test"), now_mono_ms=0)
    sim.detect_product(0)
    assert runtime.runtime_state is RuntimeState.FAULT

    runtime.send_heartbeat(now_mono_ms=100, uptime_ms=100)
    hb = [m for m in bus.published if m.topic.endswith("/system/edge01/heartbeat")][-1]
    assert hb.envelope["data"]["services_ok"] is False
