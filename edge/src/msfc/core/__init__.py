"""Cross-cutting foundation: configuration, logging, errors (Layer-independent)."""

from msfc.core.config import AppConfig, ConfigError, load_config
from msfc.core.logging_setup import configure_logging, ctx, get_logger

__all__ = [
    "AppConfig",
    "ConfigError",
    "load_config",
    "configure_logging",
    "ctx",
    "get_logger",
]
from msfc.core.errors import ConfigError  # re-exported for convenience
