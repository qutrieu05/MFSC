"""Tests for msfc.domain.enums and msfc.domain.faults."""

from __future__ import annotations

import json

import pytest

from msfc.core.errors import DomainError
from msfc.domain import (
    FAULT_CATALOG,
    LATCHED_STATES,
    NON_PRODUCTION_STATES,
    FaultCode,
    FaultSeverity,
    MachineState,
    UnknownFaultCodeError,
    lookup_fault,
)


# --------------------------------------------------------------------------- str-Enum encoding
@pytest.mark.parametrize("member,expected", [
    (MachineState.IDLE, "IDLE"),
    (MachineState.SAFE_STOP, "SAFE_STOP"),
])
def test_str_enum_json_encodes_as_contract_value(member, expected) -> None:
    """Confirms the encoding trick every domain enum relies on (see enums.py docstring)."""
    assert json.dumps({"machine_state": member}) == f'{{"machine_state": "{expected}"}}'


def test_command_action_values_match_control_cmd_schema() -> None:
    from msfc.domain import CommandAction
    assert {a.value for a in CommandAction} == {"start", "stop", "reset", "set_speed", "pusher_test"}


# --------------------------------------------------------------------------- state groupings
def test_non_production_and_latched_states_are_disjoint_from_running_family() -> None:
    running_family = {MachineState.STARTING, MachineState.RUNNING, MachineState.STOPPING}
    assert NON_PRODUCTION_STATES.isdisjoint(running_family)
    assert NON_PRODUCTION_STATES | running_family == set(MachineState)


def test_latched_states_are_a_subset_of_non_production() -> None:
    assert LATCHED_STATES <= NON_PRODUCTION_STATES
    assert LATCHED_STATES == {MachineState.SAFE_STOP, MachineState.FAULT, MachineState.ESTOP}


# --------------------------------------------------------------------------- fault catalog
def test_every_catalog_entry_has_a_valid_code_shape() -> None:
    for code, entry in FAULT_CATALOG.items():
        assert code == entry.code
        assert entry.code[0] in "FE"
        assert entry.code[1:].isdigit() and len(entry.code) == 4


def test_catalog_covers_every_code_named_in_safety_concept() -> None:
    expected = {
        "F001", "F010", "F011", "F020", "F021", "F030", "F031", "F032", "F033",
        "F040", "F041", "F050", "F051", "F052", "F060", "F070",
    }
    assert expected <= set(FAULT_CATALOG)


def test_safety_and_fault_severity_entries_are_latching_warning_entries_are_not() -> None:
    for entry in FAULT_CATALOG.values():
        if entry.severity in (FaultSeverity.SAFETY, FaultSeverity.FAULT):
            assert entry.latching, f"{entry.code} ({entry.severity}) should latch"
        if entry.severity == FaultSeverity.WARNING:
            assert not entry.latching, f"{entry.code} (WARNING) should self-clear"


def test_lookup_returns_the_catalog_entry() -> None:
    entry = lookup_fault("F001")
    assert entry.name == "ESTOP_ACTIVE"
    assert entry.severity == FaultSeverity.SAFETY
    assert entry.latching is True


def test_lookup_unknown_code_raises_with_the_code_named() -> None:
    with pytest.raises(UnknownFaultCodeError, match="F999"):
        lookup_fault("F999")


@pytest.mark.parametrize("bad_code", ["f001", "F01", "F0011", "FF01", "", "F0O1"])
def test_fault_code_construction_rejects_bad_shapes(bad_code: str) -> None:
    with pytest.raises(DomainError):
        FaultCode(code=bad_code, name="X", severity=FaultSeverity.INFO, latching=False, description="x")
