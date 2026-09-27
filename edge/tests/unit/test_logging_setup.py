"""Unit tests for the logging system (FR-OPS-01, ADR-0009)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from msfc.core.config import load_config
from msfc.core.logging_setup import (
    _HANDLER_TAG,
    HumanFormatter,
    JsonLinesFormatter,
    configure_logging,
    ctx,
    get_logger,
)

CONFIG = """
config_version = 1

[system]
line_id = "line01"
device_id = "edge01"

[logging]
console_level = "WARNING"
file_level = "DEBUG"
json_file = "test.jsonl"

[logging.levels]
"msfc.quiet" = "ERROR"
"""


@pytest.fixture()
def cfg(tmp_path: Path):
    default_path = tmp_path / "default.toml"
    default_path.write_text(CONFIG, encoding="utf-8")
    return load_config(repo_root=tmp_path, default_path=default_path,
                       site_path=tmp_path / "missing.toml", env={})


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def msfc_handlers() -> list[logging.Handler]:
    return [h for h in logging.getLogger().handlers if getattr(h, _HANDLER_TAG, False)]


def test_writes_json_lines_with_context(cfg, tmp_path: Path, restore_logging) -> None:
    log_path = configure_logging(cfg, log_dir=tmp_path / "logs")
    get_logger("msfc.test").info("product sorted", extra=ctx(product_id="7-42", action="REJECTED"))

    records = read_lines(log_path)
    assert len(records) == 1
    record = records[0]
    assert record["level"] == "INFO"
    assert record["logger"] == "msfc.test"
    assert record["msg"] == "product sorted"
    assert record["ctx"] == {"product_id": "7-42", "action": "REJECTED"}
    assert record["ts"].endswith("Z")
    assert {"module", "func", "line"} <= set(record)


def test_exception_is_recorded(cfg, tmp_path: Path, restore_logging) -> None:
    log_path = configure_logging(cfg, log_dir=tmp_path / "logs")
    log = get_logger("msfc.test")
    try:
        raise ValueError("boom")
    except ValueError:
        log.exception("unhandled", extra=ctx(fault_code="E999"))

    record = read_lines(log_path)[-1]
    assert record["level"] == "ERROR"
    assert "ValueError: boom" in record["exc"]
    assert record["ctx"]["fault_code"] == "E999"


def test_file_level_allows_debug_but_console_does_not(cfg, tmp_path: Path, restore_logging) -> None:
    log_path = configure_logging(cfg, log_dir=tmp_path / "logs")
    get_logger("msfc.test").debug("low level detail")

    assert [r["msg"] for r in read_lines(log_path)] == ["low level detail"]
    console = [h for h in msfc_handlers() if not hasattr(h, "baseFilename")]
    assert console and console[0].level == logging.WARNING


def test_per_logger_level_is_applied(cfg, tmp_path: Path, restore_logging) -> None:
    log_path = configure_logging(cfg, log_dir=tmp_path / "logs")
    get_logger("msfc.quiet").warning("should be filtered")
    get_logger("msfc.quiet").error("should pass")

    assert [r["msg"] for r in read_lines(log_path)] == ["should pass"]


def test_configure_is_idempotent(cfg, tmp_path: Path, restore_logging) -> None:
    configure_logging(cfg, log_dir=tmp_path / "logs")
    first = len(msfc_handlers())
    configure_logging(cfg, log_dir=tmp_path / "logs")
    assert first == 2
    assert len(msfc_handlers()) == 2


def test_log_directory_is_created(cfg, tmp_path: Path, restore_logging) -> None:
    target = tmp_path / "nested" / "logs"
    log_path = configure_logging(cfg, log_dir=target)
    assert target.is_dir()
    assert log_path.name == "test.jsonl"


def test_human_formatter_renders_context() -> None:
    record = logging.LogRecord("msfc.test", logging.INFO, __file__, 10, "hello", (), None)
    record.ctx = {"product_id": "7-42"}
    rendered = HumanFormatter().format(record)
    assert "msfc.test: hello {product_id=7-42}" in rendered


def test_json_formatter_handles_non_serialisable_context() -> None:
    record = logging.LogRecord("msfc.test", logging.INFO, __file__, 10, "hello", (), None)
    record.ctx = {"path": Path("C:/tmp")}
    payload = json.loads(JsonLinesFormatter().format(record))
    assert isinstance(payload["ctx"]["path"], str)
