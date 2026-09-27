"""Layered configuration loader (ADR-0008).

Order of precedence (later wins):
    1. ``config/default.toml``                      (committed, must contain every key)
    2. ``config/site.toml``                         (optional, gitignored, machine/secret values)
    3. environment variables ``MSFC__<SECTION>__<KEY>``

Design rules:
* Fail fast at startup: unknown keys, wrong types and out-of-range values raise
  :class:`~msfc.core.errors.ConfigError` naming the offending key.
* The result is an immutable dataclass tree; modules receive it via their constructor
  (no global config object).
* Environment overrides support two levels only (``SECTION__KEY``); ``[logging.levels]``
  must be set in a TOML file.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping

from msfc.core.errors import ConfigError

ENV_PREFIX = "MSFC__"
CONFIG_VERSION = 1
LOG_LEVELS = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")

_ID_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"
_DEVICE_CHARS = _ID_CHARS + "-"


# --------------------------------------------------------------------------- validators
def _check_chars(value: str, allowed: str, key: str, *, min_len: int, max_len: int) -> None:
    if not isinstance(value, str) or not (min_len <= len(value) <= max_len):
        raise ConfigError(f"must be a string of {min_len}..{max_len} characters, got {value!r}", key=key)
    bad = sorted({c for c in value if c not in allowed})
    if bad:
        raise ConfigError(f"contains disallowed character(s) {bad}; allowed: {allowed!r}", key=key)


def _check_range(value: int | float, lo: int | float, hi: int | float, key: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not (lo <= value <= hi):
        raise ConfigError(f"must be a number within [{lo}, {hi}], got {value!r}", key=key)


def _check_choice(value: str, choices: tuple[str, ...], key: str) -> None:
    if value not in choices:
        raise ConfigError(f"must be one of {list(choices)}, got {value!r}", key=key)


def _check_nonempty(value: str, key: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("must be a non-empty string", key=key)


# --------------------------------------------------------------------------- sections
@dataclass(frozen=True, slots=True)
class SystemConfig:
    """Identity of this cell/line, used in MQTT topics (see MQTT_CONTRACT section 1)."""

    line_id: str = "line01"
    device_id: str = "edge01"
    site_name: str = "msfc-lab"
    timezone: str = "Asia/Ho_Chi_Minh"

    def __post_init__(self) -> None:
        _check_chars(self.line_id, _ID_CHARS, "system.line_id", min_len=3, max_len=16)
        _check_chars(self.device_id, _DEVICE_CHARS, "system.device_id", min_len=3, max_len=32)
        _check_nonempty(self.site_name, "system.site_name")
        _check_nonempty(self.timezone, "system.timezone")


@dataclass(frozen=True, slots=True)
class MqttConfig:
    """Broker connection and timing (ADR-0004)."""

    host: str = "127.0.0.1"
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = "msfc-edge01"
    keepalive_s: int = 15
    heartbeat_interval_ms: int = 200
    command_ack_timeout_ms: int = 2000

    def __post_init__(self) -> None:
        _check_nonempty(self.host, "mqtt.host")
        _check_range(self.port, 1, 65535, "mqtt.port")
        _check_nonempty(self.client_id, "mqtt.client_id")
        _check_range(self.keepalive_s, 1, 300, "mqtt.keepalive_s")
        # SF-02: heartbeat must be published several times faster than the firmware timeout.
        _check_range(self.heartbeat_interval_ms, 50, 5000, "mqtt.heartbeat_interval_ms")
        _check_range(self.command_ack_timeout_ms, 100, 30000, "mqtt.command_ack_timeout_ms")

    @property
    def has_credentials(self) -> bool:
        return bool(self.username)


@dataclass(frozen=True, slots=True)
class PathsConfig:
    """Directories, relative to the repository root unless absolute."""

    runtime_dir: str = "runtime"
    log_dir: str = "logs"
    contracts_dir: str = "contracts"

    def __post_init__(self) -> None:
        for name in ("runtime_dir", "log_dir", "contracts_dir"):
            _check_nonempty(getattr(self, name), f"paths.{name}")


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Logging sinks and levels (ADR-0009)."""

    console_level: str = "INFO"
    file_level: str = "DEBUG"
    json_file: str = "msfc.jsonl"
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 5
    levels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_choice(self.console_level, LOG_LEVELS, "logging.console_level")
        _check_choice(self.file_level, LOG_LEVELS, "logging.file_level")
        _check_nonempty(self.json_file, "logging.json_file")
        _check_range(self.max_bytes, 4096, 1024 * 1024 * 1024, "logging.max_bytes")
        _check_range(self.backup_count, 0, 100, "logging.backup_count")
        if not isinstance(self.levels, dict):
            raise ConfigError("must be a table of logger -> level", key="logging.levels")
        for logger_name, level in self.levels.items():
            _check_nonempty(logger_name, "logging.levels")
            _check_choice(level, LOG_LEVELS, f"logging.levels.{logger_name}")


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Root configuration object handed to the services."""

    config_version: int
    repo_root: Path
    system: SystemConfig
    mqtt: MqttConfig
    paths: PathsConfig
    logging: LoggingConfig

    def path(self, which: str) -> Path:
        """Resolve a directory from ``[paths]`` against the repository root."""
        try:
            raw = getattr(self.paths, which)
        except AttributeError as exc:  # pragma: no cover - programming error
            raise ConfigError(f"unknown path name {which!r}", key="paths") from exc
        candidate = Path(raw)
        return candidate if candidate.is_absolute() else self.repo_root / candidate


# --------------------------------------------------------------------------- loading
_SECTIONS: dict[str, type] = {
    "system": SystemConfig,
    "mqtt": MqttConfig,
    "paths": PathsConfig,
    "logging": LoggingConfig,
}


def _read_toml(path: Path, *, required: bool) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise ConfigError(f"configuration file not found: {path}")
        return {}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc


def _merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _coerce(raw: str, annotation: str, key: str) -> Any:
    """Coerce an environment-variable string to the annotated field type."""
    if annotation == "str":
        return raw
    if annotation == "int":
        try:
            return int(raw)
        except ValueError as exc:
            raise ConfigError(f"expected an integer, got {raw!r}", key=key) from exc
    if annotation == "float":
        try:
            return float(raw)
        except ValueError as exc:
            raise ConfigError(f"expected a number, got {raw!r}", key=key) from exc
    if annotation == "bool":
        lowered = raw.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
        raise ConfigError(f"expected a boolean, got {raw!r}", key=key)
    raise ConfigError(f"cannot be set from an environment variable (type {annotation})", key=key)


def _apply_env(data: dict[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    result = dict(data)
    for env_key, raw in env.items():
        if not env_key.startswith(ENV_PREFIX):
            continue
        parts = env_key[len(ENV_PREFIX):].split("__")
        if len(parts) != 2:
            raise ConfigError(
                f"environment variable {env_key} must have the form {ENV_PREFIX}SECTION__KEY"
            )
        section_name, field_name = parts[0].lower(), parts[1].lower()
        section_type = _SECTIONS.get(section_name)
        if section_type is None:
            raise ConfigError(f"unknown section in environment variable {env_key}", key=section_name)
        annotations = {f.name: f.type for f in fields(section_type)}
        if field_name not in annotations:
            raise ConfigError(
                f"unknown key in environment variable {env_key}", key=f"{section_name}.{field_name}"
            )
        value = _coerce(raw, str(annotations[field_name]), f"{section_name}.{field_name}")
        section = dict(result.get(section_name, {}))
        section[field_name] = value
        result[section_name] = section
    return result


def _build(section_type: type, data: Mapping[str, Any], section_name: str):
    known = {f.name for f in fields(section_type)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ConfigError(
            f"unknown key(s): {', '.join(unknown)}; known keys: {sorted(known)}", key=section_name
        )
    try:
        return section_type(**data)
    except ConfigError:
        raise
    except TypeError as exc:
        raise ConfigError(str(exc), key=section_name) from exc


def load_config(
    *,
    repo_root: Path | None = None,
    default_path: Path | None = None,
    site_path: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> AppConfig:
    """Load, merge and validate the configuration.

    Args:
        repo_root: repository root; defaults to three levels above this file
            (``edge/src/msfc/core/config.py`` -> repo root).
        default_path: override for ``config/default.toml`` (tests).
        site_path: override for ``config/site.toml`` (tests).
        env: environment mapping; defaults to ``os.environ``.

    Raises:
        ConfigError: on a missing file, unknown key, wrong type or out-of-range value.
    """
    root = repo_root or Path(__file__).resolve().parents[4]
    defaults = _read_toml(default_path or root / "config" / "default.toml", required=True)
    site = _read_toml(site_path or root / "config" / "site.toml", required=False)
    merged = _merge(defaults, site)
    merged = _apply_env(merged, env if env is not None else os.environ)

    version = merged.pop("config_version", None)
    if version != CONFIG_VERSION:
        raise ConfigError(
            f"expected {CONFIG_VERSION}, got {version!r}; migrate the config file", key="config_version"
        )

    unknown_sections = sorted(set(merged) - set(_SECTIONS))
    if unknown_sections:
        raise ConfigError(f"unknown section(s): {', '.join(unknown_sections)}")

    built = {name: _build(dc, merged.get(name, {}), name) for name, dc in _SECTIONS.items()}
    return AppConfig(config_version=CONFIG_VERSION, repo_root=root, **built)
