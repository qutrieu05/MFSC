"""Layer-independent domain model (ARCHITECTURE.md section 7.1).

Pure dataclasses and enums with no I/O and no MQTT knowledge — every field here mirrors a
JSON Schema in ``contracts/schemas/``. This package depends only on ``msfc.core`` and is
depended on by every other layer, so it must stay small, stable and free of side effects
(CODING_STANDARDS.md rule P4).
"""

from __future__ import annotations

from msfc.domain.commands import CommandAck, ControlCommand, VerdictCommand
from msfc.domain.enums import (
    LATCHED_STATES,
    NON_PRODUCTION_STATES,
    CommandAction,
    CommandResult,
    FaultLifecycleEvent,
    FaultSeverity,
    MachineState,
    PusherState,
    RawVerdict,
    RejectReason,
    SortAction,
    SortReason,
    Verdict,
)
from msfc.domain.events import ProductDetectedEvent, ProductSortedEvent, StateChangedEvent
from msfc.domain.faults import FAULT_CATALOG, FaultCode, UnknownFaultCodeError, lookup as lookup_fault
from msfc.domain.inspection import DecisionRecord, InspectionResult, ModelInfo
from msfc.domain.state import CellStateSnapshot, Counters, FaultReport

__all__ = [
    # enums
    "MachineState", "NON_PRODUCTION_STATES", "LATCHED_STATES",
    "RawVerdict", "Verdict", "SortAction", "SortReason", "PusherState",
    "FaultSeverity", "FaultLifecycleEvent", "CommandAction", "CommandResult", "RejectReason",
    # faults
    "FaultCode", "FAULT_CATALOG", "lookup_fault", "UnknownFaultCodeError",
    # events
    "ProductDetectedEvent", "ProductSortedEvent", "StateChangedEvent",
    # inspection / decision
    "ModelInfo", "InspectionResult", "DecisionRecord",
    # commands
    "VerdictCommand", "ControlCommand", "CommandAck",
    # state
    "Counters", "CellStateSnapshot", "FaultReport",
]
