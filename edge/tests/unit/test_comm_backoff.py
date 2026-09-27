"""Tests for msfc.comm.backoff.ReconnectBackoff."""

from __future__ import annotations

import pytest

from msfc.core.errors import ContractError
from msfc.comm import ReconnectBackoff


def test_delays_grow_exponentially_then_cap() -> None:
    backoff = ReconnectBackoff(base_s=1.0, factor=2.0, max_s=10.0)
    delays = [backoff.next_delay() for _ in range(6)]
    assert delays == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0]


def test_attempt_counter_advances_with_each_call() -> None:
    backoff = ReconnectBackoff()
    assert backoff.attempt == 0
    backoff.next_delay()
    assert backoff.attempt == 1


def test_reset_restarts_from_base() -> None:
    backoff = ReconnectBackoff(base_s=1.0, factor=2.0, max_s=100.0)
    backoff.next_delay()
    backoff.next_delay()
    backoff.reset()
    assert backoff.attempt == 0
    assert backoff.next_delay() == 1.0


@pytest.mark.parametrize("kwargs,match", [
    ({"base_s": 0}, "base_s"),
    ({"base_s": -1}, "base_s"),
    ({"factor": 1}, "factor"),
    ({"factor": 0.5}, "factor"),
    ({"max_s": 0.5}, "max_s"),  # max_s < default base_s=1.0
])
def test_invalid_parameters_are_rejected(kwargs: dict, match: str) -> None:
    with pytest.raises(ContractError, match=match):
        ReconnectBackoff(**kwargs)
