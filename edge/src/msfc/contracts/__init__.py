"""MQTT contract runtime (Layer 5 support): registry, envelope, payload validation.

Single source of truth for topics/schemas is on disk (``contracts/mqtt/topics.toml``,
``contracts/schemas/*.json`` — see docs/MQTT_CONTRACT.md); this package is the only code
allowed to read those files directly (CODING_STANDARDS.md rule G5).
"""

from __future__ import annotations

from msfc.contracts.envelope import SeqCounter, build_envelope
from msfc.contracts.registry import ContractRegistry, TopicSpec
from msfc.contracts.validation import PayloadValidator

__all__ = [
    "ContractRegistry",
    "TopicSpec",
    "build_envelope",
    "SeqCounter",
    "PayloadValidator",
]
