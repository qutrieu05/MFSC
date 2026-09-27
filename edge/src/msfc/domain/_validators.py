"""Small shared validators used by dataclass ``__post_init__`` methods across msfc.domain.

Kept private (leading underscore) — this is implementation detail of the domain package,
not part of its public interface.
"""

from __future__ import annotations

import re

from msfc.core.errors import DomainError

_PRODUCT_ID_RE = re.compile(r"^[0-9]+-[0-9]+$")


def product_id(value: str, *, field: str = "product_id") -> None:
    """Validate the ``<boot_id>-<counter>`` shape required by every product_*.v1 schema."""
    if not isinstance(value, str) or not _PRODUCT_ID_RE.match(value):
        raise DomainError(f"{field} must match '<boot_id>-<counter>' (e.g. '7-42'), got {value!r}")


def unit_interval(value: float, *, field: str) -> None:
    """Validate a probability/confidence value in [0, 1]."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not (0.0 <= value <= 1.0):
        raise DomainError(f"{field} must be a number in [0, 1], got {value!r}")


def non_negative_ms(value: int, *, field: str) -> None:
    """Validate a monotonic-clock timestamp or duration in milliseconds."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DomainError(f"{field} must be a non-negative integer (ms), got {value!r}")


def non_empty_str(value: str, *, field: str, max_len: int = 200) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DomainError(f"{field} must be a non-empty string")
    if len(value) > max_len:
        raise DomainError(f"{field} must be at most {max_len} characters, got {len(value)}")
