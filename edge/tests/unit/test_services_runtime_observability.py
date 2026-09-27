"""Dashboard-phase additive extension to CellRuntime: product_history()/event_log().

Purely observational bookkeeping (see DECISIONS.md) -- these tests only prove the bookkeeping
itself; msfc.services.runtime's existing behaviour is already covered by test_services_runtime.py
and test_services_scenarios.py (unmodified by this change, still passing).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from msfc.comm import InMemoryBus
from msfc.contracts import ContractRegistry
from msfc.decision import DecisionEngine, DecisionPolicy
from msfc.domain import CommandAction, ControlCommand, ModelInfo
from msfc.services import CellIdentity, CellRuntime, DashboardEventCategory
from msfc.services.pipeline import VisionStageConfig
from msfc.sim import SimCellController
from msfc.vision import Frame, InferenceOutput, RoiConfig, Thresholds

ROI = RoiConfig(x=0, y=0, width=16, height=16, target_size=(16, 16))
MODEL = ModelInfo(name="stub", version="1")
THRESHOLDS = Thresholds(defect_at=0.5, uncertain_band=0.05)


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


class _ScriptedEngine:
    name, version = "stub", "1"

    def __init__(self) -> None:
        self._score = 0.02

    def set_score(self, score: float) -> None:
        self._score = score

    def predict(self, image: np.ndarray) -> InferenceOutput:
        return InferenceOutput(class_scores={"GOOD": 1 - self._score, "DEFECT": self._score}, timings_ms={})


class _AlwaysFrameSource:
    def read(self) -> Frame | None:
        return Frame(image=np.zeros((16, 16, 3), dtype=np.uint8), seq=0, captured_mono_ms=0, source="test")

    def close(self) -> None:
        pass


def _build(registry: ContractRegistry) -> tuple[SimCellController, CellRuntime, _ScriptedEngine]:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    identity = CellIdentity(cell_id="c1", cell_device_id=sim.device_id, edge_device_id="edge01", line_id=sim.line_id)
    engine = _ScriptedEngine()
    runtime = CellRuntime(
        identity=identity, bus=bus, registry=registry, decision_engine=DecisionEngine(DecisionPolicy()),
        vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
        frame_source=_AlwaysFrameSource(),
    )
    runtime.start()
    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="s1", action=CommandAction.START, source="test"), now_mono_ms=0)
    return sim, runtime, engine


def test_product_history_starts_empty(registry: ContractRegistry) -> None:
    _, runtime, _ = _build(registry)
    assert runtime.product_history() == ()


def test_product_history_records_each_product(registry: ContractRegistry) -> None:
    sim, runtime, engine = _build(registry)
    engine.set_score(0.02)
    sim.detect_product(0)
    engine.set_score(0.98)
    sim.detect_product(100)

    history = runtime.product_history()
    assert len(history) == 2
    assert [t.outcome.value for t in history] == ["GOOD", "DEFECT"]


def test_product_history_is_updated_with_the_sorted_event(registry: ContractRegistry) -> None:
    sim, runtime, engine = _build(registry)
    engine.set_score(0.02)
    product_id = sim.detect_product(0)
    sim.tick(500)
    sim.receive_edge_heartbeat()
    sim.arrive_at_s2(500)

    trace = runtime.product_history()[-1]
    assert trace.product_id == product_id
    assert trace.sorted_event is not None
    assert trace.sorted_event.action.value == "PASSED"


def test_product_history_respects_its_size_limit(registry: ContractRegistry) -> None:
    bus = InMemoryBus()
    sim = SimCellController(bus=bus, registry=registry)
    identity = CellIdentity(cell_id="c1", cell_device_id=sim.device_id, edge_device_id="edge01", line_id=sim.line_id)
    engine = _ScriptedEngine()
    runtime = CellRuntime(
        identity=identity, bus=bus, registry=registry, decision_engine=DecisionEngine(DecisionPolicy()),
        vision=VisionStageConfig(engine=engine, roi=ROI, thresholds=THRESHOLDS, model=MODEL),
        frame_source=_AlwaysFrameSource(), product_history_size=3,
    )
    runtime.start()
    sim.receive_edge_heartbeat()
    sim.send_command(ControlCommand(cmd_id="s1", action=CommandAction.START, source="test"), now_mono_ms=0)
    for i in range(5):
        sim.detect_product(i * 100)

    history = runtime.product_history()
    assert len(history) == 3
    assert [t.product_id for t in history] == ["1-2", "1-3", "1-4"]


def test_event_log_records_state_changes_and_products(registry: ContractRegistry) -> None:
    sim, runtime, engine = _build(registry)
    engine.set_score(0.02)
    sim.detect_product(0)

    events = runtime.event_log()
    categories = {e.category for e in events}
    assert DashboardEventCategory.STATE in categories  # BOOT->SELF_TEST->IDLE->STARTING->RUNNING
    assert DashboardEventCategory.PRODUCT in categories


def test_event_log_records_a_critical_state_change(registry: ContractRegistry) -> None:
    sim, runtime, _ = _build(registry)
    sim.press_estop(now_mono_ms=100)

    events = runtime.event_log()
    estop_events = [e for e in events if "ESTOP" in e.message]
    assert estop_events
    assert estop_events[-1].severity.value == "CRITICAL"


def test_event_log_respects_limit_and_ordering(registry: ContractRegistry) -> None:
    sim, runtime, engine = _build(registry)
    for i in range(3):
        engine.set_score(0.02)
        sim.detect_product(i * 100)

    all_events = runtime.event_log()
    last_two = runtime.event_log(limit=2)
    assert last_two == all_events[-2:]
