"""Vision/OCR inspection results and the decision engine's trace record.

Mirrors inspection_result.v1 and decision_record.v1. ``InspectionResult`` is produced by
``msfc.vision`` (Layer 3) and consumed only by ``msfc.decision`` (Layer 4) — per the layer
rules in ARCHITECTURE.md section 7.2, neither package knows MQTT exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from msfc.core.errors import DomainError
from msfc.domain import _validators as v
from msfc.domain.enums import RawVerdict, Verdict


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """Identifies the model that produced a result (inspection_result.v1 'model')."""

    name: str
    version: str
    backend: str = ""

    def __post_init__(self) -> None:
        v.non_empty_str(self.name, field="model.name", max_len=80)
        v.non_empty_str(self.version, field="model.version", max_len=40)


@dataclass(frozen=True, slots=True)
class InspectionResult:
    """One vision (or OCR) channel's verdict for one product.

    ``timings_ms`` should have at least a ``total`` key (inspection_result.v1); individual
    stage keys (``frame_select``, ``preprocess``, ``inference``, ``postprocess``) are
    optional but expected from a full pipeline (FR-VIS-08).
    """

    product_id: str
    verdict: RawVerdict
    confidence: float
    model: ModelInfo
    timings_ms: dict[str, float] = field(default_factory=dict)
    class_scores: dict[str, float] = field(default_factory=dict)
    frame_seq: int | None = None
    frame_age_ms: float | None = None
    image_ref: str | None = None

    def __post_init__(self) -> None:
        v.product_id(self.product_id)
        v.unit_interval(self.confidence, field="confidence")
        if "total" not in self.timings_ms:
            raise DomainError("timings_ms must include a 'total' key (FR-VIS-08)")
        for key, ms in self.timings_ms.items():
            if ms < 0:
                raise DomainError(f"timings_ms[{key!r}] must be >= 0, got {ms!r}")
        for cls, score in self.class_scores.items():
            v.unit_interval(score, field=f"class_scores[{cls!r}]")


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """Decision engine trace for one product (decision_record.v1, FR-DEC-03).

    ``inputs`` is a small serializable summary of what fed the decision (e.g.
    ``{"vision": {"verdict": "DEFECT", "confidence": 0.93}}``), kept for traceability
    without forcing the decision engine to depend on the inspection dataclasses' exact shape.
    """

    decision_id: str
    product_id: str
    final_verdict: Verdict
    reason_codes: tuple[str, ...]
    rules_version: str
    late: bool
    inputs: dict[str, dict[str, object]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        v.non_empty_str(self.decision_id, field="decision_id", max_len=40)
        v.product_id(self.product_id)
        v.non_empty_str(self.rules_version, field="rules_version", max_len=40)
        if not self.reason_codes:
            raise DomainError("reason_codes must not be empty (FR-DEC-01)")
        if len(self.reason_codes) > 8:
            raise DomainError("reason_codes must have at most 8 entries (verdict_cmd.v1)")
