"""Tests for msfc.comm.dedupe.DedupeFilter (MT-05)."""

from __future__ import annotations

import pytest

from msfc.core.errors import ContractError
from msfc.comm import DedupeFilter


def _envelope(device_id="esp32-cc01", boot_id=7, seq=0) -> dict:
    return {"device_id": device_id, "boot_id": boot_id, "seq": seq, "mono_ms": 0, "data": {}}


def test_first_message_passes_through() -> None:
    received = []
    filt = DedupeFilter(lambda t, e: received.append(e))
    filt("t", _envelope(seq=1))
    assert len(received) == 1


def test_exact_duplicate_seq_is_dropped() -> None:
    received = []
    filt = DedupeFilter(lambda t, e: received.append(e))
    filt("t", _envelope(seq=5))
    filt("t", _envelope(seq=5))
    assert len(received) == 1
    assert filt.dropped_count == 1


def test_different_seq_both_pass() -> None:
    received = []
    filt = DedupeFilter(lambda t, e: received.append(e))
    filt("t", _envelope(seq=1))
    filt("t", _envelope(seq=2))
    assert len(received) == 2


def test_same_seq_different_boot_id_both_pass() -> None:
    """A reboot resets the device's own seq counter; boot_id makes seq=0 after a reboot
    distinguishable from seq=0 before it."""
    received = []
    filt = DedupeFilter(lambda t, e: received.append(e))
    filt("t", _envelope(boot_id=1, seq=0))
    filt("t", _envelope(boot_id=2, seq=0))
    assert len(received) == 2


def test_same_seq_different_device_both_pass() -> None:
    received = []
    filt = DedupeFilter(lambda t, e: received.append(e))
    filt("t", _envelope(device_id="esp32-cc01", seq=0))
    filt("t", _envelope(device_id="edge01", seq=0))
    assert len(received) == 2


def test_bounded_history_forgets_the_oldest_seq() -> None:
    received = []
    filt = DedupeFilter(lambda t, e: received.append(e), max_per_device=2)
    filt("t", _envelope(seq=1))
    filt("t", _envelope(seq=2))
    filt("t", _envelope(seq=3))  # evicts seq=1 from history
    filt("t", _envelope(seq=1))  # forgotten -> treated as new, passes through again
    assert len(received) == 4


def test_missing_identity_fields_pass_through_unfiltered() -> None:
    """Envelopes missing device_id/seq are not this filter's job — they should reach the
    validator downstream so a proper E101 is raised, not be silently eaten here."""
    received = []
    filt = DedupeFilter(lambda t, e: received.append(e))
    filt("t", {"data": {}})
    filt("t", {"data": {}})
    assert len(received) == 2


def test_max_per_device_must_be_positive() -> None:
    with pytest.raises(ContractError, match="max_per_device"):
        DedupeFilter(lambda t, e: None, max_per_device=0)
