"""The Dashboard Adapter (section 1's "Dashboard Adapter/API" box): owns one demonstration
Cell -- a real (unmodified) :class:`~msfc.sim.SimCellController` wired to a real
:class:`~msfc.services.CellRuntime` over a real :class:`~msfc.comm.InMemoryBus` -- and exposes
the demo controls section 5/6 asks for.

Every "SIMULATE X" method below drives the REAL architecture (rule: "these controls are
demonstration inputs... must still pass through the existing runtime/safety architecture"):

* SIMULATE GOOD/DEFECT/UNCERTAIN -- controls the *input* the scripted vision engine reports for
  the next frame (equivalent to showing the camera a different physical part), then fires the
  real ``sim.detect_product()`` -> ``CellRuntime`` pipeline -> ``sim.arrive_at_s2()`` cycle,
  exactly like ``tests/integration/test_services_scenarios.py``.
* SIMULATE OCR FAILURE -- temporarily swaps in a deliberately-broken OCR preprocess config (bad
  target size), causing ``run_ocr_pipeline`` to raise ``OcrError`` for one cycle (a genuinely
  unavailable channel, not a content misread) -- the exact technique already proven in
  ``test_services_scenarios.py``'s OCR-unavailable scenario.
* SIMULATE HEALTH WARNING/CRITICAL -- pushes one sensor reading through
  ``CellRuntime.process_sensors()`` (never feeds the health monitor directly -- see D-061).
* SIMULATE SAFETY STOP -- calls ``sim.press_estop()``, which IS the architecturally correct way
  to simulate a physical E-stop press (``msfc.sim.engine``'s own docstring: "E-stop... modelled
  as direct method calls").
* START/STOP/RESET -- build and send real ``ControlCommand``s, exactly what an operator button
  would do.

Nothing here reaches around ``CellRuntime`` to fabricate a verdict, an OEE number, or a health
state -- this module only supplies *inputs* (sensor/vision/OCR/E-stop) and reads back whatever
the real architecture decided.
"""

from __future__ import annotations

from collections import deque
from datetime import date

import numpy as np

from msfc.analytics import (
    AnomalyThresholds,
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
from msfc.core.errors import OrchestrationError
from msfc.decision import DecisionEngine, DecisionPolicy
from msfc.domain import CommandAction, ControlCommand
from msfc.domain import ModelInfo
from msfc.ocr import FixtureOcrEngine, LabelValidationConfig, OcrOutput, PreprocessConfig
from msfc.services import CellIdentity, CellRuntime
from msfc.services.pipeline import OcrStageConfig, VisionStageConfig
from msfc.sim import SimCellController
from msfc.vision import Frame, InferenceOutput, RoiConfig, Thresholds

_ROI = RoiConfig(x=0, y=0, width=16, height=16, target_size=(16, 16))
_VISION_MODEL = ModelInfo(name="dashboard-demo-vision", version="1")
_THRESHOLDS = Thresholds(defect_at=0.5, uncertain_band=0.05)
_OCR_PREPROCESS_OK = PreprocessConfig(roi=None, target_size=(64, 32))
_OCR_PREPROCESS_BROKEN = PreprocessConfig(roi=None, target_size=(0, 0))  # forces OcrError (P6.10)
_OCR_LABEL_CONFIG = LabelValidationConfig(min_confidence=0.5)
_OCR_REFERENCE_DATE = date(2026, 9, 19)
_HEALTH_SENSOR_ID = "motor-temp-1"
# Small on purpose (P5's own "recovery_after_anomaly" fixture uses the same technique,
# documented in msfc.analytics.health_monitor's docstring): detect_baseline_anomaly looks at
# every reading still inside the window, so a demo "RECOVERY" click needs the window to be
# short enough to age out the previous anomalous reading within one click, not several seconds
# of real time waiting on background ticks.
_HEALTH_WINDOW_MS = 1500
_TRAVEL_MS = 500
_BACKGROUND_TICK_MS = 200
_HEARTBEAT_TIMEOUT_MS = 1000
_SAFE_ADVANCE_STEP_MS = 200  # well under _HEARTBEAT_TIMEOUT_MS, see DemoSession._advance


class _ScriptedVisionEngine:
    """Deterministic vision "camera" -- reports whatever score the demo control last set (same
    pattern as ``tests/integration/test_full_pipeline_mvp.py``'s ``_OracleVisionEngine``)."""

    name, version = "dashboard-demo-vision", "1"

    def __init__(self) -> None:
        self._score = 0.02  # GOOD by default

    def set_score(self, score: float) -> None:
        self._score = score

    def predict(self, image: np.ndarray) -> InferenceOutput:
        return InferenceOutput(class_scores={"GOOD": 1 - self._score, "DEFECT": self._score},
                                timings_ms={"inference": 0.5})


class _ControllableSensor:
    """A ``SensorSource`` whose next reading is set explicitly by a demo control -- never reads
    a real sensor (none exists), mirrors ``msfc.analytics.FixedSequenceSensorSource``'s explicit,
    caller-driven style."""

    def __init__(self, sensor_id: str, sensor_type: SensorType, *, initial_value: float) -> None:
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self._value = initial_value

    def set_value(self, value: float) -> None:
        self._value = value

    def read(self, *, mono_ms: int) -> SensorMeasurement:
        return SensorMeasurement(sensor_id=self.sensor_id, sensor_type=self.sensor_type, mono_ms=mono_ms,
                                  value=self._value, unit="degC")


class _AlwaysFrameSource:
    """The demo always has "a frame" (there is no real camera) -- matches P6's own demo/test
    convention (``_AlwaysFrameSource`` in test_services_scenarios.py)."""

    def read(self) -> Frame | None:
        return Frame(image=np.zeros((16, 16, 3), dtype=np.uint8), seq=0, captured_mono_ms=0, source="dashboard-demo")

    def close(self) -> None:
        pass


class DemoSession:
    """One demonstration cell: real SimCellController + real CellRuntime + real InMemoryBus.
    A single process-lifetime instance is owned by the FastAPI app (see ``api.py``)."""

    def __init__(self, *, contracts_root) -> None:
        self.registry = ContractRegistry.load(contracts_root)
        self.bus = InMemoryBus()
        self.sim = SimCellController(bus=self.bus, registry=self.registry,
                                      heartbeat_timeout_ms=_HEARTBEAT_TIMEOUT_MS)
        identity = CellIdentity(cell_id="s1-demo-cell", cell_device_id=self.sim.device_id,
                                 edge_device_id="dashboard-edge01", line_id=self.sim.line_id)

        self._vision_engine = _ScriptedVisionEngine()
        self._ocr_engine = FixtureOcrEngine()
        self._ocr_engine.set_next_output(OcrOutput(raw_text="EXP 2027-01-01", confidence=0.95))
        self._ocr_preprocess = _OCR_PREPROCESS_OK

        self.machine_monitor = MachineMonitor(ProductionSession(
            SessionConfig(planned_production_time_ms=600_000, ideal_cycle_time_ms=500), started_at_mono_ms=0,
        ))
        self.health_monitor = MachineHealthMonitor(
            baselines={_HEALTH_SENSOR_ID: HealthBaseline(sensor_type=SensorType.TEMPERATURE,
                                                           expected_min=20.0, expected_max=40.0)},
            thresholds={_HEALTH_SENSOR_ID: AnomalyThresholds(warning_deviation=2.0, anomaly_deviation=5.0,
                                                              critical_deviation=10.0)},
            window_ms=_HEALTH_WINDOW_MS,
        )
        self._sensor = _ControllableSensor(_HEALTH_SENSOR_ID, SensorType.TEMPERATURE, initial_value=25.0)

        self.runtime = CellRuntime(
            identity=identity, bus=self.bus, registry=self.registry,
            decision_engine=DecisionEngine(DecisionPolicy(deadline_ms=300)),
            vision=VisionStageConfig(engine=self._vision_engine, roi=_ROI, thresholds=_THRESHOLDS,
                                      model=_VISION_MODEL),
            frame_source=_AlwaysFrameSource(),
            ocr=self._ocr_stage_config(),
            machine_monitor=self.machine_monitor, health_monitor=self.health_monitor, sensors=[self._sensor],
            bridge_health_critical_to_oee=True,
        )
        self.runtime.start()

        self._mono_ms = 0
        self._uptime_ms = 0
        self._product_seq = 0
        self._refresh_heartbeat()

    @property
    def mono_ms(self) -> int:
        """This demo cell's current simulated clock, milliseconds."""
        return self._mono_ms

    # ------------------------------------------------------------------ clock / heartbeat
    def _ocr_stage_config(self) -> OcrStageConfig:
        return OcrStageConfig(engine=self._ocr_engine, preprocess=self._ocr_preprocess,
                               label_config=_OCR_LABEL_CONFIG, reference_date=_OCR_REFERENCE_DATE)

    def _advance(self, delta_ms: int) -> None:
        """The one place sim time moves forward. Chunked into steps no larger than
        ``_SAFE_ADVANCE_STEP_MS`` (comfortably under the Cell Controller's own
        ``heartbeat_timeout_ms``), each immediately followed by a heartbeat refresh -- a single
        large jump (e.g. advancing past the machine-health window in one call) would otherwise
        itself trip a spurious COMM_LOSS fault, since the sim checks staleness at the instant of
        ``tick()``, before this method's own refresh can run. A real bug caught while adding the
        health-recovery demo control -- see DECISIONS.md."""
        remaining = delta_ms
        while remaining > 0:
            step = min(remaining, _SAFE_ADVANCE_STEP_MS)
            self._mono_ms += step
            self.sim.tick(self._mono_ms)
            self._uptime_ms += step
            self._refresh_heartbeat()
            remaining -= step

    def _refresh_heartbeat(self) -> None:
        self.sim.receive_edge_heartbeat()
        self.runtime.send_heartbeat(now_mono_ms=self._mono_ms, uptime_ms=self._uptime_ms)

    def background_tick(self) -> None:
        """Called periodically by the API's background task (see api.py) to keep the demo
        "alive" (fresh heartbeat, moving clock) even with no user interaction -- exactly what a
        real Edge Server's continuous 5 Hz heartbeat already does in the real architecture."""
        self._advance(_BACKGROUND_TICK_MS)

    # ------------------------------------------------------------------ operator controls
    def send_start(self) -> None:
        self._refresh_heartbeat()
        self.sim.send_command(ControlCommand(cmd_id=self._next_cmd_id(), action=CommandAction.START,
                                              source="dashboard"), now_mono_ms=self._mono_ms)

    def send_stop(self) -> None:
        self._refresh_heartbeat()
        self.sim.send_command(ControlCommand(cmd_id=self._next_cmd_id(), action=CommandAction.STOP,
                                              source="dashboard"), now_mono_ms=self._mono_ms)

    def send_reset(self) -> None:
        """Mirrors a real operator's recovery sequence (SAF-05: release then reset) -- never
        clears ESTOP by itself if the (simulated) button is still physically held."""
        if self.sim.state.value == "ESTOP":
            self.sim.release_estop(now_mono_ms=self._mono_ms)
        self.sim.local_reset(now_mono_ms=self._mono_ms)
        self._refresh_heartbeat()

    _cmd_seq = 0

    def _next_cmd_id(self) -> str:
        self._cmd_seq += 1
        return f"dash-{self._cmd_seq}"

    # ------------------------------------------------------------------ demonstration controls (section 5)
    def simulate_good(self) -> str:
        self._vision_engine.set_score(0.02)
        return self._run_one_product_cycle()

    def simulate_defect(self) -> str:
        self._vision_engine.set_score(0.98)
        return self._run_one_product_cycle()

    def simulate_uncertain(self) -> str:
        self._vision_engine.set_score(0.50)  # dead center of the uncertain band (defect_at=0.5+-0.05)
        return self._run_one_product_cycle()

    def simulate_ocr_failure(self) -> str:
        """One cycle with the OCR channel genuinely UNAVAILABLE (OcrError), not a content
        misread -- vision alone must still carry the decision if it is available."""
        original = self._ocr_preprocess
        self._ocr_preprocess = _OCR_PREPROCESS_BROKEN
        self.runtime.ocr = self._ocr_stage_config()
        try:
            return self._run_one_product_cycle()
        finally:
            self._ocr_preprocess = original
            self.runtime.ocr = self._ocr_stage_config()

    def simulate_health_warning(self) -> None:
        self._sensor.set_value(42.5)  # 2.5 above expected_max=40 -> WARNING band
        self.runtime.process_sensors(mono_ms=self._mono_ms)

    def simulate_health_critical(self) -> None:
        self._sensor.set_value(55.0)  # 15 above expected_max=40 -> CRITICAL band
        self.runtime.process_sensors(mono_ms=self._mono_ms)

    def simulate_health_recovery(self) -> None:
        """Advances the clock past the health window first so the previous anomalous reading
        has genuinely aged out (not just been out-voted) -- a real recovery, not a fudge."""
        self._advance(_HEALTH_WINDOW_MS + 100)
        self._sensor.set_value(25.0)
        self.runtime.process_sensors(mono_ms=self._mono_ms)

    def simulate_safety_stop(self) -> None:
        """The architecturally correct way to simulate a physical E-stop press -- see module
        docstring; never a hidden shortcut into MachineState."""
        self.sim.press_estop(now_mono_ms=self._mono_ms)

    def _run_one_product_cycle(self) -> str:
        self._refresh_heartbeat()
        product_id = self.sim.detect_product(self._mono_ms)
        self._advance(_TRAVEL_MS)
        self.sim.arrive_at_s2(self._mono_ms)
        return product_id

    # ------------------------------------------------------------------ full demo (section 6)
    def run_full_demo(self) -> None:
        """The scripted 14-step sequence from the PO's directive section 6. Deterministic --
        no randomness. Every step is one of the real controls above, nothing new."""
        self.send_start()                      # 1-3: startup, ready, RUNNING
        self.simulate_health_recovery()        # 4: healthy machine
        self.simulate_good()                   # 5
        self.simulate_good()                   # 6
        self.simulate_defect()                 # 7
        self.simulate_ocr_failure()            # 8: OCR/label verification scenario (unavailable channel)
        self.simulate_health_warning()         # 9: machine-health warning
        self.simulate_safety_stop()            # 10-11: safety/E-STOP, safe stop
        product_id = self.sim.detect_product(self._mono_ms + 10)
        self._advance(_TRAVEL_MS)
        self.sim.arrive_at_s2(self._mono_ms)   # denied product, fail-closed at S2 (keeps FIFO in sync)
        self.send_reset()                      # 12: recovery per P2 rules
        self.send_start()                      # 13: production resumes
        self.simulate_good()                   # 13: one more product to prove resumption
        # 14: caller reads final summary via the DTO builders in api.py


def build_default_session(*, contracts_root) -> DemoSession:
    """Convenience factory used by api.py; kept separate so a future test can construct a
    DemoSession with a different contracts_root without touching api.py."""
    return DemoSession(contracts_root=contracts_root)


__all__ = ["DemoSession", "build_default_session"]
