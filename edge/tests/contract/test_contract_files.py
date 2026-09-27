"""Validate the MQTT contract files (FR-COM-02, FR-COM-03, ADR-0004).

The registry ``contracts/mqtt/topics.toml`` is the single source of truth for topics.
These tests make the registry, the JSON schemas and docs/MQTT_CONTRACT.md stay consistent,
so firmware and Edge Server cannot drift apart silently.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

PLACEHOLDER = re.compile(r"^\{[a-z_]+\}$")
NAME_RE = re.compile(r"^[a-z0-9_]+$")
SCHEMA_NAME_RE = re.compile(r"^[a-z0-9_]+\.v[0-9]+$")


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> dict:
    with (repo_root / "contracts" / "mqtt" / "topics.toml").open("rb") as handle:
        return tomllib.load(handle)


@pytest.fixture(scope="module")
def schema_dir(repo_root: Path) -> Path:
    return repo_root / "contracts" / "schemas"


@pytest.fixture(scope="module")
def contract_doc(repo_root: Path) -> str:
    return (repo_root / "docs" / "MQTT_CONTRACT.md").read_text(encoding="utf-8")


def test_registry_header_is_complete(registry: dict) -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", registry["contract_version"])
    assert registry["root"] == "factory"
    assert registry["message_classes"] and registry["subsystems"]
    assert registry["topic"], "registry must define at least one topic"


def test_topic_keys_and_patterns_are_unique(registry: dict) -> None:
    keys = [entry["key"] for entry in registry["topic"]]
    patterns = [entry["pattern"] for entry in registry["topic"]]
    assert len(keys) == len(set(keys)), "duplicate topic key"
    assert len(patterns) == len(set(patterns)), "duplicate topic pattern"


def test_topic_patterns_follow_the_grammar(registry: dict) -> None:
    classes = set(registry["message_classes"])
    subsystems = set(registry["subsystems"])
    for entry in registry["topic"]:
        segments = entry["pattern"].split("/")
        assert segments[0] == registry["root"], entry["key"]
        assert PLACEHOLDER.match(segments[1]), f"{entry['key']}: line_id must be a placeholder"
        assert segments[2] in subsystems, f"{entry['key']}: unknown subsystem {segments[2]}"
        assert PLACEHOLDER.match(segments[3]), f"{entry['key']}: device_id must be a placeholder"
        assert segments[4] in classes, f"{entry['key']}: unknown message class {segments[4]}"
        assert len(segments) in (5, 6), f"{entry['key']}: pattern has too many segments"
        if len(segments) == 6:
            assert NAME_RE.match(segments[5]), f"{entry['key']}: bad name segment"


def test_topic_metadata_is_valid(registry: dict) -> None:
    for entry in registry["topic"]:
        key = entry["key"]
        assert entry["qos"] in (0, 1, 2), key
        assert isinstance(entry["retain"], bool), key
        assert isinstance(entry["phase"], int) and 0 <= entry["phase"] <= 7, key
        assert entry["status"] in ("active", "draft"), key
        assert entry["publisher"] and entry["subscribers"], key
        assert entry["rate"], key
        assert SCHEMA_NAME_RE.match(entry["schema"]), f"{key}: bad schema name {entry['schema']}"


def test_commands_are_never_retained(registry: dict) -> None:
    """A retained command would be re-delivered on reconnect and could restart the line."""
    for entry in registry["topic"]:
        if "/cmd/" in entry["pattern"] or entry["pattern"].endswith("/cmd"):
            assert entry["retain"] is False, f"{entry['key']} must not be retained"
            assert entry["qos"] == 1, f"{entry['key']} must use QoS 1"


def test_state_and_status_are_retained(registry: dict) -> None:
    for entry in registry["topic"]:
        cls = entry["pattern"].split("/")[4]
        if cls in ("status", "state"):
            assert entry["retain"] is True, f"{entry['key']} should be retained"


def test_heartbeats_are_qos0_and_not_retained(registry: dict) -> None:
    for entry in registry["topic"]:
        if entry["pattern"].split("/")[4] == "heartbeat":
            assert entry["qos"] == 0 and entry["retain"] is False, entry["key"]


def test_every_referenced_schema_exists_and_is_valid_json(registry: dict, schema_dir: Path) -> None:
    for entry in registry["topic"]:
        path = schema_dir / f"{entry['schema']}.json"
        assert path.exists(), f"{entry['key']}: missing schema file {path.name}"
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$id"] == f"msfc/{entry['schema']}"
        assert schema["type"] == "object"
        assert schema["required"], f"{path.name}: schema must list required fields"
        assert schema["x-status"] in ("active", "draft")


def test_envelope_schema_defines_the_common_fields(schema_dir: Path) -> None:
    envelope = json.loads((schema_dir / "envelope.v1.json").read_text(encoding="utf-8"))
    assert set(envelope["required"]) == {"schema", "device_id", "seq", "mono_ms", "data"}
    assert envelope["additionalProperties"] is False


def test_active_topics_use_active_schemas(registry: dict, schema_dir: Path) -> None:
    for entry in registry["topic"]:
        schema = json.loads((schema_dir / f"{entry['schema']}.json").read_text(encoding="utf-8"))
        if entry["status"] == "active":
            assert schema["x-status"] == "active", (
                f"{entry['key']} is active but schema {entry['schema']} is draft"
            )


def test_no_orphan_schema_files(registry: dict, schema_dir: Path) -> None:
    referenced = {entry["schema"] for entry in registry["topic"]} | {"envelope.v1"}
    on_disk = {path.stem for path in schema_dir.glob("*.json")}
    orphans = sorted(on_disk - referenced)
    assert not orphans, f"schema files not referenced by any topic: {orphans}"


def test_documentation_lists_every_topic_key(registry: dict, contract_doc: str) -> None:
    missing = sorted(entry["key"] for entry in registry["topic"] if entry["key"] not in contract_doc)
    assert not missing, f"docs/MQTT_CONTRACT.md does not document: {missing}"


def test_safety_relevant_channels_are_documented_as_such(registry: dict, contract_doc: str) -> None:
    """SF-02/SF-03/SF-04 depend on these channels; the contract must flag them."""
    for key in ("system.heartbeat", "safety.heartbeat"):
        entry = next(item for item in registry["topic"] if item["key"] == key)
        assert "SAFETY-RELEVANT" in entry["rate"], f"{key}: mark the rate field as safety-relevant"
    assert "SF-02" in contract_doc and "SF-03" in contract_doc
