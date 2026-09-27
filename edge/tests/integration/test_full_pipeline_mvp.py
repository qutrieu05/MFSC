"""End-to-end MVP pipeline test (P1.2+P1.4+P1.6+P1.7 wired together):

    Camera/Test Input -> Vision/AI -> Decision Engine -> Command -> ESP32 Mock
        -> Motor/Servo Mock -> GOOD/DEFECT result

This is exactly the pipeline diagram in the founder's directive, built entirely from real
(tested elsewhere in isolation) components: :class:`~msfc.vision.SyntheticFrameSource`-style
samples, :class:`~msfc.decision.DecisionEngine`, and :class:`~msfc.sim.SimCellController`
talking over a real :class:`~msfc.comm.InMemoryBus` using the real contract (registry +
envelope + schema validation) — nothing here is a special-cased shortcut.

There is no ``msfc.services`` orchestrator yet (that is P1.14, out of scope for this
session) — the small ``_Pipeline`` helper below plays that role for this test only.
Building the real orchestrator later should only ever need to call the same public methods
used here.

**Scope, and an honest finding from building this test.** These tests prove the *wiring* is
correct: a DEFECT decision reliably causes a REJECTED sort with the pusher acting; a GOOD
decision reliably causes PASSED; no verdict in time reliably fails closed to REJECTED; a
heartbeat loss reliably faults the line. Model *accuracy* is a separate concern
(test_vision_evaluation.py's job). While wiring this test up, ``ClassicCvBaseline``
calibrated against the synthetic generator's default position jitter (±8 px on a 128 px
canvas) plus per-pixel sensor noise turned out to barely separate GOOD from either DEFECT
type in absolute terms (empirically: mean abs-diff-from-template ≈ 21.9 for GOOD vs ≈ 21.9–
23.2 for DEFECT) — a real, worth-reporting limitation of a plain "distance from an averaged,
jitter-blurred template" classifier, not a bug in the wiring. Most tests below therefore use
a small deterministic label-aware stub engine to isolate wiring correctness from that known
model limitation; one dedicated test (``test_real_classic_cv_baseline_plugs_into_the_pipeline``)
still exercises the real ``ClassicCvBaseline`` to prove it satisfies the ``InferenceEngine``
interface end-to-end, without asserting it gets every answer right.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from msfc.comm import InMemoryBus
from msfc.contracts import ContractRegistry, PayloadValidator
from msfc.decision import DecisionEngine, DecisionPolicy
from msfc.domain import CommandAction, ControlCommand, MachineState, ModelInfo, PusherState
from msfc.sim import SimCellController
from msfc.vision import (
    ClassicCvBaseline,
    Frame,
    InferenceOutput,
    LabeledSample,
    RoiConfig,
    Thresholds,
    generate_sample,
    postprocess,
    preprocess,
)

ROI = RoiConfig(x=0, y=0, width=128, height=128, target_size=(128, 128))
DETECT_TO_S2_TRAVEL_MS = 500  # >> expected decision latency; see NFR-PERF-01's real target


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


class _OracleVisionEngine:
    """Deterministic, label-aware stand-in for a calibrated vision engine.

    Used by the wiring-focused tests in this file (see module docstring for why): it lets
    those tests assert exact GOOD/DEFECT routing without depending on
    ``ClassicCvBaseline``'s real, currently-limited discriminative power on this synthetic
    dataset. It implements the same :class:`~msfc.vision.InferenceEngine` interface a real
    engine would.
    """

    name = "oracle_stub"
    version = "0.0.1"

    def __init__(self) -> None:
        self._next_label: str | None = None

    def set_next_label(self, label: str) -> None:
        self._next_label = label

    def predict(self, image: np.ndarray) -> InferenceOutput:
        if self._next_label == "DEFECT":
            scores = {"GOOD": 0.02, "DEFECT": 0.98}
        else:
            scores = {"GOOD": 0.98, "DEFECT": 0.02}
        return InferenceOutput(class_scores=scores, timings_ms={"inference": 0.1})


class _Pipeline:
    """The P1.14 orchestrator's job, played by hand for this test only (see module docstring)."""

    def __init__(self, registry: ContractRegistry, *, engine=None) -> None:
        self.bus = InMemoryBus()
        self.sim = SimCellController(bus=self.bus, registry=registry, heartbeat_timeout_ms=1000)
        self.engine = engine or _OracleVisionEngine()
        self.model = ModelInfo(name=self.engine.name, version=self.engine.version)
        self.decision = DecisionEngine(DecisionPolicy(deadline_ms=300))
        self.thresholds = Thresholds(defect_at=0.5, uncertain_band=0.05)
        self.now = 0

    def start(self, *, now_mono_ms: int = 0):
        """Bring the line up: heartbeat already flowing (realistic — the Edge Server
        publishes at 5 Hz continuously, well before an operator issues START), then START."""
        self.sim.receive_edge_heartbeat()
        ack = self.sim.send_command(
            ControlCommand(cmd_id="start", action=CommandAction.START, source="test"), now_mono_ms=now_mono_ms
        )
        self.now = now_mono_ms
        return ack

    def run_one_product(self, sample: LabeledSample, *, decision_latency_ms: int = 40) -> dict:
        """Feed one already-known sample through the whole stack; returns a small trace
        dict for the test to assert on."""
        t_detect = self.now
        self.sim.tick(t_detect)
        self.sim.receive_edge_heartbeat()
        product_id = self.sim.detect_product(t_detect)

        frame = Frame(image=sample.image, seq=0, captured_mono_ms=t_detect, source="synthetic")
        processed = preprocess(frame, ROI)
        if hasattr(self.engine, "set_next_label"):
            self.engine.set_next_label(sample.label)
        output = self.engine.predict(processed)
        inspection = postprocess(output, self.thresholds, product_id=product_id, model=self.model, frame=frame)

        t_decision = t_detect + decision_latency_ms
        record = self.decision.decide(product_id, [inspection],
                                       detected_at_mono_ms=t_detect, now_mono_ms=t_decision)
        verdict_cmd = self.decision.to_verdict_command(record, confidence=inspection.confidence)
        self.sim.receive_verdict(verdict_cmd, now_mono_ms=t_decision)

        t_s2 = t_detect + DETECT_TO_S2_TRAVEL_MS
        self.sim.tick(t_s2)
        self.sim.receive_edge_heartbeat()
        sorted_event = self.sim.arrive_at_s2(t_s2)

        self.now = t_s2 + 50  # gap before the next product
        return {
            "product_id": product_id,
            "ground_truth": sample.label,
            "inspection_verdict": inspection.verdict.value,
            "decision_verdict": record.final_verdict.value,
            "sorted_action": sorted_event.action.value,
            "sorted_reason": sorted_event.reason.value,
            "margin_ms": sorted_event.margin_ms,
        }


def test_pipeline_starts_and_reaches_running(registry: ContractRegistry) -> None:
    pipeline = _Pipeline(registry)
    ack = pipeline.start()
    assert ack.result.value == "DONE"
    assert pipeline.sim.state is MachineState.RUNNING


def test_pipeline_mvp_routes_good_and_defect_correctly_end_to_end(registry: ContractRegistry) -> None:
    pipeline = _Pipeline(registry)
    pipeline.start()

    rng = np.random.default_rng(123)
    samples = [
        LabeledSample(image=generate_sample(rng, "GOOD"), label="GOOD", sub_label=None, session_id="pipeline"),
        LabeledSample(image=generate_sample(rng, "DEFECT", "MARK"), label="DEFECT", sub_label="MARK",
                      session_id="pipeline"),
        LabeledSample(image=generate_sample(rng, "GOOD"), label="GOOD", sub_label=None, session_id="pipeline"),
        LabeledSample(image=generate_sample(rng, "DEFECT", "MARK"), label="DEFECT", sub_label="MARK",
                      session_id="pipeline"),
    ]

    traces = [pipeline.run_one_product(s) for s in samples]

    for trace in traces:
        # The wiring invariant this test exists to prove: whatever the AI/Decision Engine
        # decided, the Cell Controller's sort action must follow it exactly, AND (since the
        # oracle engine is label-correct by construction) the ground truth too.
        assert trace["decision_verdict"] == trace["ground_truth"], trace
        if trace["decision_verdict"] == "GOOD":
            assert trace["sorted_action"] == "PASSED", trace
            assert trace["sorted_reason"] == "VERDICT_GOOD", trace
        else:
            assert trace["sorted_action"] == "REJECTED", trace
            assert trace["sorted_reason"] == "VERDICT_DEFECT", trace
        assert trace["margin_ms"] is not None and trace["margin_ms"] > 0, (
            "verdict must arrive with positive margin before the product reaches S2 (NFR-PERF-01)"
        )

    # product_ids were issued in strictly increasing order (timing/tracking simulation)
    counters = [int(t["product_id"].split("-")[1]) for t in traces]
    assert counters == sorted(counters) == list(range(len(traces)))

    snap = pipeline.sim.snapshot()
    assert snap.counters.detected == len(samples)
    assert snap.counters.passed == 2 and snap.counters.rejected == 2
    assert snap.pusher is PusherState.RETRACTED  # settled after the last sort
    assert snap.machine_state is MachineState.RUNNING  # never faulted during a clean run


def test_pipeline_mvp_fails_closed_when_no_verdict_arrives_in_time(registry: ContractRegistry) -> None:
    """ADR-0005's core promise: an AI/decision outage must degrade to rejecting the
    product, never to silently passing a potentially-defective one."""
    pipeline = _Pipeline(registry)
    pipeline.start()

    product_id = pipeline.sim.detect_product(0)
    # Deliberately do NOT run vision/decision/receive_verdict for this product.
    pipeline.sim.tick(DETECT_TO_S2_TRAVEL_MS)
    pipeline.sim.receive_edge_heartbeat()
    event = pipeline.sim.arrive_at_s2(DETECT_TO_S2_TRAVEL_MS)

    assert event.product_id == product_id
    assert event.action.value == "REJECTED"
    assert event.reason.value == "NO_DECISION"
    assert event.verdict_received is False
    fault_codes = [m.envelope["data"]["code"] for m in pipeline.bus.published if m.topic.endswith("/fault")]
    assert "F033" in fault_codes


def test_pipeline_mvp_enters_fault_on_heartbeat_loss_and_recovers(registry: ContractRegistry) -> None:
    """Fault handling: the Cell Controller must go safe on its own when the Edge
    Server/AI stack disappears, then accept a controlled recovery once it is back."""
    pipeline = _Pipeline(registry)
    pipeline.start()

    # One product goes through normally first, proving the fault below is a real transition,
    # not just "it never started".
    rng = np.random.default_rng(1)
    sample = LabeledSample(image=generate_sample(rng, "GOOD"), label="GOOD", sub_label=None, session_id="p")
    trace = pipeline.run_one_product(sample)
    assert trace["sorted_action"] == "PASSED"
    assert pipeline.sim.state is MachineState.RUNNING

    # Now the Edge Server (and with it, vision/decision) disappears.
    fault_tick_time = pipeline.now + 2000
    pipeline.sim.tick(fault_tick_time)  # no more receive_edge_heartbeat() calls from here

    snap = pipeline.sim.snapshot()
    assert snap.machine_state is MachineState.FAULT
    assert "F010" in snap.active_faults
    assert snap.safety_relay_closed is False
    assert snap.motor_output_pct == 0.0

    # Recovery: Edge Server comes back, operator resets.
    recover_time = fault_tick_time + 100
    pipeline.sim.tick(recover_time)
    pipeline.sim.receive_edge_heartbeat()
    ack = pipeline.sim.send_command(ControlCommand(cmd_id="reset-1", action=CommandAction.RESET, source="test"),
                                     now_mono_ms=recover_time)
    assert ack.result.value == "DONE"
    assert pipeline.sim.state is MachineState.IDLE


def test_every_published_message_across_a_full_run_validates(registry: ContractRegistry) -> None:
    """Contract self-compliance over a realistic multi-product run, not just a single
    unit-level message — same check as test_sim_cell_controller's version, exercised here
    against the full pipeline's message traffic."""
    pipeline = _Pipeline(registry)
    pipeline.start()
    rng = np.random.default_rng(7)
    for label, sub in [("GOOD", None), ("DEFECT", "MARK"), ("DEFECT", "SCRATCH"), ("GOOD", None)]:
        sample = LabeledSample(image=generate_sample(rng, label, sub), label=label, sub_label=sub,
                                session_id="p")
        pipeline.run_one_product(sample)

    validator = PayloadValidator(registry)
    assert len(pipeline.bus.published) > 4
    for message in pipeline.bus.published:
        match = registry.match_topic(message.topic)
        assert match is not None, f"unregistered topic: {message.topic}"
        spec, _ = match
        validator.validate_for_topic(spec.key, message.envelope)


def test_real_classic_cv_baseline_plugs_into_the_pipeline(registry: ContractRegistry) -> None:
    """Proves the real (not stubbed) ClassicCvBaseline satisfies the InferenceEngine
    interface all the way through the pipeline, without asserting it gets every answer
    right — see the module docstring's "honest finding" for why accuracy is not asserted
    here (that is test_vision_evaluation.py's job)."""
    refs = [generate_sample(np.random.default_rng(seed), "GOOD") for seed in range(10)]
    real_engine = ClassicCvBaseline(reference_images=refs, defect_threshold=1.2, sensitivity=0.3)
    pipeline = _Pipeline(registry, engine=real_engine)
    pipeline.start()

    rng = np.random.default_rng(50)
    sample = LabeledSample(image=generate_sample(rng, "DEFECT", "MARK"), label="DEFECT",
                            sub_label="MARK", session_id="p")
    trace = pipeline.run_one_product(sample)

    # Self-consistency, not ground-truth correctness: whatever the real engine decided must
    # still be routed correctly by decision+sim.
    if trace["decision_verdict"] == "GOOD":
        assert trace["sorted_action"] == "PASSED"
    else:
        assert trace["sorted_action"] == "REJECTED"
    assert pipeline.sim.state is MachineState.RUNNING
