"""Shared pytest fixtures for the Edge Server test suite."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root (contains config/, contracts/, edge/, firmware/)."""
    return REPO_ROOT


@pytest.fixture()
def default_config_path(repo_root: Path) -> Path:
    return repo_root / "config" / "default.toml"


@pytest.fixture()
def restore_logging():
    """Save/restore root logger state so logging tests cannot leak into other tests."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    yield
    for handler in list(root.handlers):
        if handler not in saved_handlers:
            root.removeHandler(handler)
            handler.close()
    for handler in saved_handlers:
        if handler not in root.handlers:
            root.addHandler(handler)
    root.setLevel(saved_level)
