"""Enumerations shared by every layer (ARCHITECTURE.md section 7.1, MQTT_CONTRACT.md).

Every enum mixes in ``str`` so ``json.dumps`` encodes members using their contract value
directly (verified: a ``str``-mixin Enum member serializes as its plain string content,
not as ``ClassName.MEMBER``), and so encoded values match the JSON Schemas in
``contracts/schemas/`` byte for byte.
"""

from __future__ import annotations

from enum import Enum


class MachineState(str, Enum):
    """Cell Controller state machine (ARCHITECTURE.md section 4, cell_state.v1 schema)."""

    BOOT = "BOOT"
    SELF_TEST = "SELF_TEST"
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    SAFE_STOP = "SAFE_STOP"
    FAULT = "FAULT"
    ESTOP = "ESTOP"


#: States in which the cell is not producing and the pusher must stay retracted (SF-07).
NON_PRODUCTION_STATES = frozenset(
    {MachineState.BOOT, MachineState.SELF_TEST, MachineState.IDLE, MachineState.SAFE_STOP,
     MachineState.FAULT, MachineState.ESTOP}
)

#: States that are latched: they persist until an explicit, controlled reset (SAFETY_CONCEPT.md section 4).
LATCHED_STATES = frozenset({MachineState.SAFE_STOP, MachineState.FAULT, MachineState.ESTOP})


class RawVerdict(str, Enum):
    """Signal-level verdict from one inspection channel (vision, OCR). FR-VIS-05."""

    GOOD = "GOOD"
    DEFECT = "DEFECT"
    UNCERTAIN = "UNCERTAIN"


class Verdict(str, Enum):
    """Final verdict sent to the Cell Controller. verdict_cmd.v1 restricts this to two values."""

    GOOD = "GOOD"
    DEFECT = "DEFECT"


class SortAction(str, Enum):
    """Outcome recorded by the Cell Controller for one product (product_sorted.v1)."""

    PASSED = "PASSED"
    REJECTED = "REJECTED"


class SortReason(str, Enum):
    """Reason enum constrained by product_sorted.v1."""

    VERDICT_GOOD = "VERDICT_GOOD"
    VERDICT_DEFECT = "VERDICT_DEFECT"
    NO_DECISION = "NO_DECISION"
    TRACKING_MISMATCH = "TRACKING_MISMATCH"


class PusherState(str, Enum):
    """Actuator position (cell_state.v1). SF-07: must be RETRACTED outside RUNNING."""

    RETRACTED = "RETRACTED"
    EXTENDING = "EXTENDING"
    EXTENDED = "EXTENDED"
    RETRACTING = "RETRACTING"


class FaultSeverity(str, Enum):
    """Severity band for a fault (SAFETY_CONCEPT.md section 5)."""

    INFO = "INFO"
    WARNING = "WARNING"
    FAULT = "FAULT"
    SAFETY = "SAFETY"


class FaultLifecycleEvent(str, Enum):
    """Whether a fault report is being raised or cleared (fault.v1)."""

    RAISED = "RAISED"
    CLEARED = "CLEARED"


class CommandAction(str, Enum):
    """Operator/control command actions accepted by the Cell Controller (control_cmd.v1)."""

    START = "start"
    STOP = "stop"
    RESET = "reset"
    SET_SPEED = "set_speed"
    PUSHER_TEST = "pusher_test"


class CommandResult(str, Enum):
    """Outcome of a control command (cmd_ack.v1)."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DONE = "DONE"
    FAILED = "FAILED"


#: Standard rejection reasons, from MQTT_CONTRACT.md section 5.
class RejectReason(str, Enum):
    ESTOP_LATCHED = "estop_latched"
    FAULT_LATCHED = "fault_latched"
    SAFE_STOP_LATCHED = "safe_stop_latched"
    NOT_IDLE = "not_idle"
    NOT_RUNNING = "not_running"
    CAUSE_NOT_CLEARED = "cause_not_cleared"
    REMOTE_RESET_FORBIDDEN = "remote_reset_forbidden"
    INVALID_PARAMS = "invalid_params"
    SAFETY_VISION_UNAVAILABLE = "safety_vision_unavailable"
    EDGE_HEARTBEAT_MISSING = "edge_heartbeat_missing"
