"""Tests for msfc.contracts.envelope (build_envelope, SeqCounter)."""

from __future__ import annotations

import pytest

from msfc.core.errors import ContractError
from msfc.contracts import SeqCounter, build_envelope


def test_build_envelope_minimal() -> None:
    env = build_envelope(schema="fault.v1", device_id="edge01", seq=0, mono_ms=100,
                          data={"code": "F010", "name": "COMM_LOSS_EDGE",
                                "severity": "FAULT", "event": "RAISED", "latched": True})
    assert env["schema"] == "fault.v1"
    assert "boot_id" not in env and "ts" not in env


def test_build_envelope_with_boot_id_and_ts() -> None:
    env = build_envelope(schema="device_status.v1", device_id="esp32-cc01", seq=1, mono_ms=5,
                          data={"online": True}, boot_id=7, ts="2026-09-18T10:00:00.000Z")
    assert env["boot_id"] == 7 and env["ts"].endswith("Z")


@pytest.mark.parametrize("seq", [-1, 1.5, True])
def test_build_envelope_rejects_bad_seq(seq) -> None:
    with pytest.raises(ContractError, match="seq"):
        build_envelope(schema="s", device_id="d", seq=seq, mono_ms=0, data={})


@pytest.mark.parametrize("mono_ms", [-1, 2.5, True])
def test_build_envelope_rejects_bad_mono_ms(mono_ms) -> None:
    with pytest.raises(ContractError, match="mono_ms"):
        build_envelope(schema="s", device_id="d", seq=0, mono_ms=mono_ms, data={})


def test_build_envelope_rejects_non_dict_data() -> None:
    with pytest.raises(ContractError, match="data must be a dict"):
        build_envelope(schema="s", device_id="d", seq=0, mono_ms=0, data="oops")  # type: ignore[arg-type]


def test_build_envelope_rejects_negative_boot_id() -> None:
    with pytest.raises(ContractError, match="boot_id"):
        build_envelope(schema="s", device_id="d", seq=0, mono_ms=0, data={}, boot_id=-1)


# --------------------------------------------------------------------------- SeqCounter
def test_seq_counter_starts_at_zero_by_default() -> None:
    counter = SeqCounter()
    assert counter.peek() == 0
    assert counter.next() == 0
    assert counter.next() == 1
    assert counter.peek() == 2


def test_seq_counter_custom_start() -> None:
    counter = SeqCounter(start=100)
    assert counter.next() == 100


def test_seq_counter_rejects_negative_start() -> None:
    with pytest.raises(ContractError):
        SeqCounter(start=-1)
