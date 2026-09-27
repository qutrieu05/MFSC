"""Tests for msfc.contracts.registry against both the real registry and small fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from msfc.core.errors import ContractError
from msfc.contracts import ContractRegistry


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


# --------------------------------------------------------------------------- loading the real registry
def test_load_default_root_finds_the_real_registry() -> None:
    """No-arg load() must resolve to <repo_root>/contracts without being told where it is."""
    registry = ContractRegistry.load()
    assert registry.contract_version.count(".") == 2
    assert "conveyor.event.product_detected" in registry.keys()


def test_real_registry_has_25_topics(registry: ContractRegistry) -> None:
    assert len(registry.keys()) == 25


def test_topic_lookup_known_key(registry: ContractRegistry) -> None:
    spec = registry.topic("conveyor.cmd.verdict")
    assert spec.schema == "verdict_cmd.v1"
    assert spec.qos == 1 and spec.retain is False


def test_topic_lookup_unknown_key_names_it(registry: ContractRegistry) -> None:
    with pytest.raises(ContractError, match="unknown topic key 'nope'"):
        registry.topic("nope")


# --------------------------------------------------------------------------- format_topic
def test_format_topic_fills_line_and_device(registry: ContractRegistry) -> None:
    topic = registry.format_topic("conveyor.status", device_id="esp32-cc01")
    assert topic == "factory/line01/conveyor/esp32-cc01/status"


def test_format_topic_respects_explicit_line_id(registry: ContractRegistry) -> None:
    topic = registry.format_topic("system.heartbeat", device_id="edge01", line_id="line02")
    assert topic.startswith("factory/line02/")


def test_format_topic_event_names_are_baked_into_the_key_not_parameterised(registry: ContractRegistry) -> None:
    """Each event has its own topic key with the name already literal in the pattern —
    there is no {name} placeholder to fill in (see format_topic's docstring)."""
    topic = registry.format_topic("conveyor.event.product_detected", device_id="esp32-cc01")
    assert topic == "factory/line01/conveyor/esp32-cc01/event/product_detected"


# --------------------------------------------------------------------------- match_topic
def test_match_topic_round_trips_format_topic(registry: ContractRegistry) -> None:
    topic = registry.format_topic("conveyor.event.product_sorted", device_id="esp32-cc01")
    result = registry.match_topic(topic)
    assert result is not None
    spec, params = result
    assert spec.key == "conveyor.event.product_sorted"
    assert params == {"line_id": "line01", "device_id": "esp32-cc01"}


def test_match_topic_captures_line_and_device_only(registry: ContractRegistry) -> None:
    result = registry.match_topic("factory/line01/conveyor/esp32-cc01/status")
    assert result is not None
    spec, params = result
    assert spec.key == "conveyor.status"
    assert set(params) == {"line_id", "device_id"}


def test_match_topic_unrecognised_topic_returns_none(registry: ContractRegistry) -> None:
    assert registry.match_topic("factory/line01/unknown/dev/status") is None


# --------------------------------------------------------------------------- schema loading
def test_load_schema_returns_and_caches(registry: ContractRegistry) -> None:
    schema = registry.load_schema("fault.v1")
    assert schema["$id"] == "msfc/fault.v1"
    assert registry.load_schema("fault.v1") is schema  # same object: cached


def test_load_schema_unknown_name_raises(registry: ContractRegistry) -> None:
    with pytest.raises(ContractError, match="schema file not found"):
        registry.load_schema("does_not_exist.v1")


def test_envelope_schema_matches_load_schema(registry: ContractRegistry) -> None:
    assert registry.envelope_schema() is registry.load_schema("envelope.v1")


# --------------------------------------------------------------------------- malformed registries (fixtures)
def _write(tmp_path: Path, topics_toml: str) -> Path:
    root = tmp_path / "contracts"
    (root / "mqtt").mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "mqtt" / "topics.toml").write_text(topics_toml, encoding="utf-8")
    return root


_HEADER = """
contract_version = "0.1.0"
root = "factory"
default_line_id = "line01"
message_classes = ["status", "event"]
subsystems = ["conveyor"]
"""


def test_missing_registry_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="not found"):
        ContractRegistry.load(tmp_path / "contracts")


def test_invalid_toml_raises(tmp_path: Path) -> None:
    root = _write(tmp_path, "not [ valid toml")
    with pytest.raises(ContractError, match="invalid TOML"):
        ContractRegistry.load(root)


def test_unknown_subsystem_is_rejected(tmp_path: Path) -> None:
    root = _write(tmp_path, _HEADER + """
[[topic]]
key = "x.status"
pattern = "factory/{line_id}/nosuch/{device_id}/status"
publisher = "a"
subscribers = ["b"]
qos = 1
retain = true
schema = "device_status.v1"
rate = "on change"
phase = 1
status = "active"
""")
    with pytest.raises(ContractError, match="unknown subsystem"):
        ContractRegistry.load(root)


def test_unknown_message_class_is_rejected(tmp_path: Path) -> None:
    root = _write(tmp_path, _HEADER + """
[[topic]]
key = "x.bogus"
pattern = "factory/{line_id}/conveyor/{device_id}/bogus"
publisher = "a"
subscribers = ["b"]
qos = 1
retain = true
schema = "device_status.v1"
rate = "on change"
phase = 1
status = "active"
""")
    with pytest.raises(ContractError, match="unknown message class"):
        ContractRegistry.load(root)


def test_duplicate_key_is_rejected(tmp_path: Path) -> None:
    entry = """
[[topic]]
key = "x.status"
pattern = "factory/{line_id}/conveyor/{device_id}/status"
publisher = "a"
subscribers = ["b"]
qos = 1
retain = true
schema = "device_status.v1"
rate = "on change"
phase = 1
status = "active"
"""
    root = _write(tmp_path, _HEADER + entry + entry)
    with pytest.raises(ContractError, match="duplicate topic key"):
        ContractRegistry.load(root)


def test_missing_field_names_the_key(tmp_path: Path) -> None:
    root = _write(tmp_path, _HEADER + """
[[topic]]
key = "x.status"
pattern = "factory/{line_id}/conveyor/{device_id}/status"
publisher = "a"
subscribers = ["b"]
qos = 1
retain = true
schema = "device_status.v1"
rate = "on change"
phase = 1
""")
    with pytest.raises(ContractError, match="'x.status'"):
        ContractRegistry.load(root)
