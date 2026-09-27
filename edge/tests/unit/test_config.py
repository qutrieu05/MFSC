"""Unit tests for the layered configuration loader (FR-OPS-02, ADR-0008)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from msfc.core.config import CONFIG_VERSION, AppConfig, load_config
from msfc.core.errors import ConfigError

MINIMAL = """
config_version = 1

[system]
line_id = "line01"
device_id = "edge01"

[mqtt]
host = "127.0.0.1"
port = 1883

[logging]
console_level = "INFO"
"""


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def load(tmp_path: Path, text: str, *, site: str | None = None, env: dict[str, str] | None = None) -> AppConfig:
    default_path = write(tmp_path, "default.toml", text)
    site_path = write(tmp_path, "site.toml", site) if site is not None else tmp_path / "missing.toml"
    return load_config(repo_root=tmp_path, default_path=default_path, site_path=site_path, env=env or {})


# --------------------------------------------------------------------------- happy path
def test_repo_default_config_loads(repo_root: Path, default_config_path: Path) -> None:
    cfg = load_config(repo_root=repo_root, default_path=default_config_path,
                      site_path=repo_root / "config" / "does-not-exist.toml", env={})
    assert cfg.config_version == CONFIG_VERSION
    assert cfg.system.line_id == "line01"
    assert cfg.mqtt.port == 1883
    assert cfg.logging.console_level == "INFO"
    assert cfg.path("log_dir") == repo_root / "logs"


def test_defaults_fill_missing_keys(tmp_path: Path) -> None:
    cfg = load(tmp_path, MINIMAL)
    assert cfg.mqtt.keepalive_s == 15  # dataclass default
    assert cfg.paths.runtime_dir == "runtime"
    assert cfg.logging.levels == {}


def test_config_is_immutable(tmp_path: Path) -> None:
    cfg = load(tmp_path, MINIMAL)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.mqtt.port = 1884  # type: ignore[misc]


def test_absolute_path_is_kept(tmp_path: Path) -> None:
    absolute = (tmp_path / "abs-logs").as_posix()
    cfg = load(tmp_path, MINIMAL + f'\n[paths]\nlog_dir = "{absolute}"\n')
    assert cfg.path("log_dir") == Path(absolute)


# --------------------------------------------------------------------------- layering
def test_site_overrides_default(tmp_path: Path) -> None:
    cfg = load(tmp_path, MINIMAL, site='[mqtt]\nhost = "192.168.1.10"\nusername = "edge_server"\n')
    assert cfg.mqtt.host == "192.168.1.10"
    assert cfg.mqtt.has_credentials is True
    assert cfg.mqtt.port == 1883  # untouched by the site file


def test_env_overrides_site(tmp_path: Path) -> None:
    cfg = load(tmp_path, MINIMAL, site='[mqtt]\nport = 1884\n', env={"MSFC__MQTT__PORT": "1885"})
    assert cfg.mqtt.port == 1885


def test_env_value_is_coerced_to_field_type(tmp_path: Path) -> None:
    cfg = load(tmp_path, MINIMAL, env={"MSFC__MQTT__KEEPALIVE_S": "30"})
    assert cfg.mqtt.keepalive_s == 30 and isinstance(cfg.mqtt.keepalive_s, int)


# --------------------------------------------------------------------------- failures
def test_missing_default_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(repo_root=tmp_path, default_path=tmp_path / "nope.toml", env={})


def test_invalid_toml_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="invalid TOML"):
        load(tmp_path, "config_version = 1\n[mqtt\nport = 1883\n")


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    """A typo such as 'prot' instead of 'port' must fail at startup, not silently."""
    with pytest.raises(ConfigError, match="unknown key"):
        load(tmp_path, MINIMAL.replace("port = 1883", "prot = 1883"))


def test_unknown_section_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="unknown section"):
        load(tmp_path, MINIMAL + "\n[vision]\nfps = 30\n")


def test_out_of_range_value_names_the_key(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"mqtt\.port"):
        load(tmp_path, MINIMAL.replace("port = 1883", "port = 0"))


def test_invalid_log_level_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"logging\.console_level"):
        load(tmp_path, MINIMAL.replace('console_level = "INFO"', 'console_level = "VERBOSE"'))


def test_invalid_per_logger_level_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"logging\.levels\.msfc\.comm"):
        load(tmp_path, MINIMAL + '\n[logging.levels]\n"msfc.comm" = "TRACE"\n')


def test_invalid_line_id_characters_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"system\.line_id"):
        load(tmp_path, MINIMAL.replace('line_id = "line01"', 'line_id = "Line/01"'))


def test_config_version_mismatch_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config_version"):
        load(tmp_path, MINIMAL.replace("config_version = 1", "config_version = 99"))


@pytest.mark.parametrize(
    "env,message",
    [
        ({"MSFC__MQTT": "x"}, "SECTION__KEY"),
        ({"MSFC__VISION__FPS": "30"}, "unknown section"),
        ({"MSFC__MQTT__PORTT": "1883"}, "unknown key"),
        ({"MSFC__MQTT__PORT": "abc"}, "expected an integer"),
    ],
)
def test_bad_environment_variables_are_rejected(tmp_path: Path, env: dict[str, str], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load(tmp_path, MINIMAL, env=env)
