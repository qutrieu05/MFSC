"""Error types shared by all MSFC Edge Server layers.

Rules (CODING_STANDARDS):
* Every module raises MsfcError subclasses, never bare Exception.
* Error messages must name the offending value/key so troubleshooting is possible.
"""

from __future__ import annotations


class MsfcError(Exception):
    """Base class for all MSFC errors."""


class ConfigError(MsfcError):
    """Configuration is missing, malformed, or out of range.

    Raised at startup only (fail fast); never during the control path.
    """

    def __init__(self, message: str, *, key: str | None = None) -> None:
        self.key = key
        super().__init__(f"[{key}] {message}" if key else message)


class ContractError(MsfcError):
    """Topic registry or payload schema problem (see docs/MQTT_CONTRACT.md)."""


class PayloadInvalidError(ContractError):
    """Incoming MQTT payload does not match its schema (fault code E101)."""

    def __init__(self, message: str, *, topic: str | None = None) -> None:
        self.topic = topic
        super().__init__(f"[{topic}] {message}" if topic else message)


class DomainError(MsfcError):
    """A domain model invariant was violated (see msfc.domain)."""


class VisionError(MsfcError):
    """Camera, frame source, or inference pipeline failure (see msfc.vision)."""


class DecisionError(MsfcError):
    """Decision engine configuration or evaluation failure (see msfc.decision)."""


class SimulationError(MsfcError):
    """Cell Controller simulator reached an invalid or unmodelled state (see msfc.sim)."""


class OcrError(MsfcError):
    """OCR preprocessing, engine, extraction, or validation failure (see msfc.ocr)."""


class OeeError(MsfcError):
    """OEE/machine-monitoring calculation or session failure (see msfc.analytics)."""


class HealthError(MsfcError):
    """Machine-health sensor, feature, baseline, anomaly-detection, or model failure
    (see msfc.analytics's health_* modules)."""


class OrchestrationError(MsfcError):
    """Pipeline orchestration or Cell Runtime lifecycle failure (see msfc.services)."""
