"""Logging setup: human-readable console + machine-readable JSON lines file (ADR-0009).

Usage::

    cfg = load_config()
    log_path = configure_logging(cfg)
    log = get_logger(__name__)
    log.info("product sorted", extra=ctx(product_id="7-42", action="REJECTED"))

Context fields go through ``extra=ctx(...)`` so both sinks can render them and so
analysis scripts can filter the JSONL file by ``ctx.product_id``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from msfc.core.config import AppConfig

_HANDLER_TAG = "_msfc_handler"
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"ctx", "message", "asctime"}


def ctx(**fields: Any) -> dict[str, Any]:
    """Build the ``extra`` mapping for a log call: ``log.info("msg", extra=ctx(a=1))``."""
    return {"ctx": fields}


def get_logger(name: str) -> logging.Logger:
    """Return a module logger; names should start with ``msfc.`` for level overrides."""
    return logging.getLogger(name)


def _iso_now(created: float) -> str:
    return (
        datetime.fromtimestamp(created, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _record_ctx(record: logging.LogRecord) -> dict[str, Any]:
    fields = dict(getattr(record, "ctx", {}) or {})
    # Also accept ad-hoc extras passed without ctx(), e.g. extra={"product_id": "7-42"}.
    for key, value in record.__dict__.items():
        if key not in _RESERVED and not key.startswith("_"):
            fields.setdefault(key, value)
    return fields


class JsonLinesFormatter(logging.Formatter):
    """One JSON object per line; stable field names for later analysis."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _iso_now(record.created),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        fields = _record_ctx(record)
        if fields:
            payload["ctx"] = fields
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """Console format: ``12:01:02.345 INFO     msfc.vision: message {product_id=7-42}``."""

    default_time_format = "%H:%M:%S"
    default_msec_format = "%s.%03d"

    def __init__(self) -> None:
        super().__init__(fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        fields = _record_ctx(record)
        if fields:
            rendered = " ".join(f"{k}={v}" for k, v in fields.items())
            base = f"{base} {{{rendered}}}"
        return base


def _remove_previous_handlers(root: logging.Logger) -> None:
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_TAG, False):
            root.removeHandler(handler)
            handler.close()


def configure_logging(cfg: AppConfig, *, log_dir: Path | None = None) -> Path:
    """Install console + JSONL handlers and apply per-logger levels.

    Idempotent: calling it again replaces the handlers it installed previously
    (handlers installed by other code, e.g. pytest, are left untouched).

    Returns:
        Path of the JSON lines log file.
    """
    directory = log_dir or cfg.path("log_dir")
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / cfg.logging.json_file

    root = logging.getLogger()
    _remove_previous_handlers(root)

    console = logging.StreamHandler()
    console.setLevel(cfg.logging.console_level)
    console.setFormatter(HumanFormatter())
    setattr(console, _HANDLER_TAG, True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=cfg.logging.max_bytes,
        backupCount=cfg.logging.backup_count,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setLevel(cfg.logging.file_level)
    file_handler.setFormatter(JsonLinesFormatter())
    setattr(file_handler, _HANDLER_TAG, True)

    root.addHandler(console)
    root.addHandler(file_handler)
    # Root must pass the most verbose of the two sinks; handlers filter individually.
    root.setLevel(min(console.level, file_handler.level))

    for logger_name, level in cfg.logging.levels.items():
        logging.getLogger(logger_name).setLevel(level)

    return log_path
