"""Edge AI Cell Platform orchestration (Layer 6, Phase 6 — pre-declared since Phase 0 in
ARCHITECTURE.md section 7.1/7.2 as "vong doi service, orchestrator, inspection/safety/oee/
health service, chan doan").

Composes msfc.vision, msfc.ocr, msfc.decision, msfc.analytics and msfc.comm/msfc.contracts into
one hardware-independent pipeline + runtime. Per the layer dependency rules
(edge/tests/unit/test_layer_dependencies.py), this package may import every processing layer
EXCEPT msfc.sim, msfc.dashboard and msfc.cli -- it talks to the Cell Controller (real or
simulated) only through msfc.comm.MessageBus and the contract registry, never by importing the
simulator directly. This is what makes "replace the simulator with real firmware" (P6.19) a
property of the code, not just a claim in a document.

This package NEVER overrides safety (P6.4): it cannot import msfc.sim or firmware, and even
where it observes the Cell Controller's state, it can only choose not to originate a new
verdict/command (msfc.services.safety_gate) -- it never clears a latch, forces an actuator, or
treats AI/OCR/health as a safety controller.
"""

from __future__ import annotations

from msfc.services.codec import decode
from msfc.services.health_pipeline import bridge_critical_events, ingest_sensors
from msfc.services.pipeline import OcrStageConfig, VisionStageConfig, run_product_cycle
from msfc.services.platform_model import (
    NON_OPERATIONAL_RUNTIME_STATES,
    CellIdentity,
    CellSnapshot,
    DashboardEvent,
    DashboardEventCategory,
    DashboardEventSeverity,
    PipelineOutcome,
    ProductCycleTrace,
    RuntimeState,
    SubsystemHealth,
)
from msfc.services.runtime import CellRuntime
from msfc.services.safety_gate import SafetyGateResult, evaluate_safety_gate
from msfc.services.timing import PipelineTiming, StageTimer, StageTiming, TimingStats

__all__ = [
    "CellIdentity",
    "RuntimeState",
    "NON_OPERATIONAL_RUNTIME_STATES",
    "PipelineOutcome",
    "ProductCycleTrace",
    "SubsystemHealth",
    "CellSnapshot",
    "DashboardEvent",
    "DashboardEventCategory",
    "DashboardEventSeverity",
    "decode",
    "SafetyGateResult",
    "evaluate_safety_gate",
    "VisionStageConfig",
    "OcrStageConfig",
    "run_product_cycle",
    "ingest_sensors",
    "bridge_critical_events",
    "StageTimer",
    "StageTiming",
    "PipelineTiming",
    "TimingStats",
    "CellRuntime",
]
