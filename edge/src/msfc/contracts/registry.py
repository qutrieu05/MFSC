"""Topic registry loader (FR-COM-02): reads ``contracts/mqtt/topics.toml``.

This is the *only* place in the Edge Server that should read ``topics.toml`` or a schema
file directly — every other module gets topics and schemas through a :class:`ContractRegistry`
instance (CODING_STANDARDS.md rule G5, "no hard-coded topic strings").
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from msfc.core.errors import ContractError

_SEGMENT_RE = re.compile(r"^\{(\w+)\}$")


@dataclass(frozen=True, slots=True)
class TopicSpec:
    """One row of the topic registry (contracts/mqtt/topics.toml).

    ``pattern`` uses ``{name}`` placeholders (``{line_id}``, ``{device_id}``, and — for
    topics with a ``/{name}`` segment — a topic-specific placeholder such as ``{name}``
    literally in the TOML; see MQTT_CONTRACT.md section 1).
    """

    key: str
    pattern: str
    publisher: str
    subscribers: tuple[str, ...]
    qos: int
    retain: bool
    schema: str
    rate: str
    phase: int
    status: str


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile a topic pattern (with ``{placeholder}`` segments) to a matching regex."""
    parts: list[str] = []
    for segment in pattern.split("/"):
        m = _SEGMENT_RE.match(segment)
        parts.append(f"(?P<{m.group(1)}>[^/]+)" if m else re.escape(segment))
    return re.compile("^" + "/".join(parts) + "$")


class ContractRegistry:
    """In-memory view of the topic registry plus a cache of loaded JSON Schemas.

    Construct via :meth:`load`; the constructor itself is an implementation detail.
    """

    def __init__(
        self,
        *,
        contract_version: str,
        root: str,
        line_id: str,
        topics: dict[str, TopicSpec],
        schemas_dir: Path,
    ) -> None:
        self._contract_version = contract_version
        self._root = root
        self._default_line_id = line_id
        self._topics = topics
        self._regex = {key: _pattern_to_regex(spec.pattern) for key, spec in topics.items()}
        self._schemas_dir = schemas_dir
        self._schema_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------ loading
    @classmethod
    def load(cls, contracts_root: Path | None = None) -> "ContractRegistry":
        """Load the registry from ``<contracts_root>/mqtt/topics.toml``.

        Args:
            contracts_root: directory containing ``mqtt/`` and ``schemas/``. Defaults to
                ``<repo_root>/contracts`` (resolved relative to this file), matching
                ``config/default.toml``'s ``paths.contracts_dir`` default.

        Raises:
            ContractError: missing/invalid file, or a topic entry referencing an unknown
                subsystem or message class.
        """
        root_dir = contracts_root or Path(__file__).resolve().parents[4] / "contracts"
        toml_path = root_dir / "mqtt" / "topics.toml"
        if not toml_path.exists():
            raise ContractError(f"topic registry not found: {toml_path}")
        try:
            with toml_path.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ContractError(f"invalid TOML in {toml_path}: {exc}") from exc

        subsystems = set(data.get("subsystems", ()))
        classes = set(data.get("message_classes", ()))
        topics: dict[str, TopicSpec] = {}
        for raw in data.get("topic", []):
            spec = cls._parse_topic(raw, subsystems=subsystems, classes=classes)
            if spec.key in topics:
                raise ContractError(f"duplicate topic key in registry: {spec.key!r}")
            topics[spec.key] = spec

        return cls(
            contract_version=data.get("contract_version", "0.0.0"),
            root=data.get("root", "factory"),
            line_id=data.get("default_line_id", "line01"),
            topics=topics,
            schemas_dir=root_dir / "schemas",
        )

    @staticmethod
    def _parse_topic(raw: dict, *, subsystems: set[str], classes: set[str]) -> TopicSpec:
        try:
            segments = raw["pattern"].split("/")
        except KeyError as exc:
            raise ContractError(f"topic entry missing 'pattern': {raw}") from exc
        if len(segments) < 5:
            raise ContractError(f"topic {raw.get('key')!r} pattern too short: {raw['pattern']!r}")
        if segments[2] not in subsystems:
            raise ContractError(f"topic {raw.get('key')!r} has unknown subsystem {segments[2]!r}")
        if segments[4] not in classes:
            raise ContractError(f"topic {raw.get('key')!r} has unknown message class {segments[4]!r}")
        try:
            return TopicSpec(
                key=raw["key"],
                pattern=raw["pattern"],
                publisher=raw["publisher"],
                subscribers=tuple(raw["subscribers"]),
                qos=int(raw["qos"]),
                retain=bool(raw["retain"]),
                schema=raw["schema"],
                rate=raw["rate"],
                phase=int(raw["phase"]),
                status=raw["status"],
            )
        except KeyError as exc:
            raise ContractError(f"topic {raw.get('key')!r} missing field {exc}") from exc

    # ------------------------------------------------------------------ accessors
    @property
    def contract_version(self) -> str:
        return self._contract_version

    @property
    def default_line_id(self) -> str:
        return self._default_line_id

    def keys(self) -> tuple[str, ...]:
        return tuple(self._topics)

    def topic(self, key: str) -> TopicSpec:
        """Return the spec for *key*, or raise ContractError naming the unknown key."""
        try:
            return self._topics[key]
        except KeyError as exc:
            raise ContractError(f"unknown topic key {key!r}; known keys: {sorted(self._topics)}") from exc

    def format_topic(self, key: str, *, device_id: str, line_id: str | None = None) -> str:
        """Render the concrete MQTT topic string for *key*.

        Every topic key in the registry already fully specifies its own literal path (e.g.
        ``conveyor.event.product_detected`` and ``conveyor.event.product_sorted`` are two
        separate keys, each with its event name baked into the pattern) — there is no
        generic ``{name}`` placeholder to fill in at format time. Only ``{line_id}`` and
        ``{device_id}`` vary per call.
        """
        spec = self.topic(key)
        rendered = spec.pattern.replace("{line_id}", line_id or self._default_line_id)
        return rendered.replace("{device_id}", device_id)

    def match_topic(self, topic: str) -> tuple[TopicSpec, dict[str, str]] | None:
        """Return ``(spec, {"line_id": ..., "device_id": ...})`` for a concrete topic
        string, or ``None`` if it matches no entry in the registry (fault code E103)."""
        for key, regex in self._regex.items():
            m = regex.match(topic)
            if m:
                return self._topics[key], m.groupdict()
        return None

    # ------------------------------------------------------------------ schemas
    def schema_path(self, schema_name: str) -> Path:
        return self._schemas_dir / f"{schema_name}.json"

    def load_schema(self, schema_name: str) -> dict:
        """Load and cache the JSON Schema document named *schema_name* (e.g. ``'fault.v1'``)."""
        if schema_name in self._schema_cache:
            return self._schema_cache[schema_name]
        path = self.schema_path(schema_name)
        if not path.exists():
            raise ContractError(f"schema file not found for {schema_name!r}: {path}")
        try:
            with path.open(encoding="utf-8") as handle:
                schema = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ContractError(f"invalid JSON in schema {path}: {exc}") from exc
        self._schema_cache[schema_name] = schema
        return schema

    def envelope_schema(self) -> dict:
        return self.load_schema("envelope.v1")
