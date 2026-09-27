"""Tests for msfc.comm.topic_match (MQTT wildcard matching)."""

from __future__ import annotations

import pytest

from msfc.core.errors import ContractError
from msfc.comm import compile_topic_filter


@pytest.mark.parametrize("filt,topic,expected", [
    ("factory/line01/conveyor/esp32-cc01/status", "factory/line01/conveyor/esp32-cc01/status", True),
    ("factory/line01/conveyor/esp32-cc01/status", "factory/line01/conveyor/edge01/status", False),
    ("factory/line01/conveyor/+/status", "factory/line01/conveyor/esp32-cc01/status", True),
    ("factory/line01/conveyor/+/status", "factory/line01/conveyor/esp32-cc01/state", False),
    ("factory/+/+/+/fault", "factory/line01/conveyor/esp32-cc01/fault", True),
    ("factory/+/+/+/fault", "factory/line01/conveyor/esp32-cc01/event/fault", False),
    ("factory/line01/conveyor/+/event/#", "factory/line01/conveyor/esp32-cc01/event/product_detected", True),
    ("factory/line01/conveyor/+/event/#", "factory/line01/conveyor/esp32-cc01/event", True),
    ("factory/line01/conveyor/+/event/#", "factory/line01/conveyor/esp32-cc01/state", False),
    ("#", "factory/line01/conveyor/esp32-cc01/status", True),
    ("#", "", True),
])
def test_topic_filter_matching(filt: str, topic: str, expected: bool) -> None:
    assert bool(compile_topic_filter(filt).match(topic)) is expected


def test_plus_matches_exactly_one_level_not_zero() -> None:
    pattern = compile_topic_filter("factory/+/status")
    assert not pattern.match("factory/status")
    assert not pattern.match("factory/a/b/status")


def test_hash_in_the_middle_is_rejected() -> None:
    with pytest.raises(ContractError, match="'#'"):
        compile_topic_filter("factory/#/status")
