"""Offline evaluation harness (VT-01..04): the only place accuracy numbers are allowed to
come from. Every report is tagged with ``data_source`` so a synthetic smoke-test result can
never be mistaken for a claim about real products (D-026, docs/QA_PLAN.md section 8).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from msfc.core.errors import VisionError
from msfc.domain import ModelInfo
from msfc.vision.frame import Frame
from msfc.vision.inference import InferenceEngine
from msfc.vision.postprocess import Thresholds, postprocess
from msfc.vision.preprocess import RoiConfig, preprocess
from msfc.vision.synthetic import LabeledSample

_DATA_SOURCES = ("synthetic", "phone", "real")
_UNCERTAIN_POLICIES = ("as_defect", "as_good")


@dataclass(frozen=True, slots=True)
class EvalReport:
    """VT-01 output: everything docs/DATASET_SPEC.md section 8 requires be reported."""

    data_source: str
    n_samples: int
    accuracy: float
    precision_defect: float
    recall_defect: float
    f1_defect: float
    confusion: dict[str, int]  # {"tp": .., "fp": .., "tn": .., "fn": ..}, DEFECT = positive
    recall_by_sub_label: dict[str, float]
    false_positive_ids: tuple[int, ...]
    false_negative_ids: tuple[int, ...]
    latency_ms: dict[str, float]  # {"mean", "p50", "p95", "max"}
    uncertain_count: int
    uncertain_policy: str

    @property
    def is_synthetic(self) -> bool:
        return self.data_source == "synthetic"


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, round(fraction * (len(sorted_values) - 1)))
    return sorted_values[index]


def evaluate(
    samples: Sequence[LabeledSample],
    engine: InferenceEngine,
    thresholds: Thresholds,
    *,
    roi: RoiConfig,
    data_source: str,
    uncertain_policy: str = "as_defect",
) -> EvalReport:
    """Run *engine* over *samples* and compute the full VT-01 report.

    Args:
        samples: ground-truth labeled samples (docs/DATASET_SPEC.md section 6: for a real
            report these must come from a held-out capture *session*, never mixed with
            training data).
        data_source: one of ``"synthetic"``, ``"phone"``, ``"real"`` — stamped onto the
            report so it can never be read as a claim it is not (D-026).
        uncertain_policy: how an UNCERTAIN verdict is scored for accuracy/precision/recall
            purposes (the decision engine's actual policy for *production* may differ —
            see FR-DEC-04; this only affects how this report counts things).

    Raises:
        VisionError: empty *samples*, or an unknown *data_source*/*uncertain_policy*.
    """
    if not samples:
        raise VisionError("evaluate() requires at least one sample")
    if data_source not in _DATA_SOURCES:
        raise VisionError(f"data_source must be one of {_DATA_SOURCES}, got {data_source!r}")
    if uncertain_policy not in _UNCERTAIN_POLICIES:
        raise VisionError(f"uncertain_policy must be one of {_UNCERTAIN_POLICIES}, got {uncertain_policy!r}")

    model = ModelInfo(name=engine.name, version=engine.version)
    y_true: list[str] = []
    y_pred: list[str] = []
    sub_labels: list[str | None] = []
    latencies: list[float] = []
    fp_ids: list[int] = []
    fn_ids: list[int] = []
    uncertain_count = 0

    for idx, sample in enumerate(samples):
        frame = Frame(image=sample.image, seq=idx, captured_mono_ms=0, source=data_source)
        processed = preprocess(frame, roi)
        output = engine.predict(processed)
        latencies.append(output.timings_ms.get("inference", output.timings_ms.get("total", 0.0)))

        result = postprocess(output, thresholds, product_id=f"0-{idx}", model=model, frame=frame)
        predicted = result.verdict.value
        if predicted == "UNCERTAIN":
            uncertain_count += 1
            predicted = "DEFECT" if uncertain_policy == "as_defect" else "GOOD"

        y_true.append(sample.label)
        y_pred.append(predicted)
        sub_labels.append(sample.sub_label)
        if sample.label == "GOOD" and predicted == "DEFECT":
            fp_ids.append(idx)
        if sample.label == "DEFECT" and predicted == "GOOD":
            fn_ids.append(idx)

    tp = sum(1 for t, p in zip(y_true, y_pred) if t == "DEFECT" and p == "DEFECT")
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == "GOOD" and p == "DEFECT")
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == "GOOD" and p == "GOOD")
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == "DEFECT" and p == "GOOD")

    accuracy = (tp + tn) / len(samples)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    recall_by_sub: dict[str, float] = {}
    for sub in sorted({s for s in sub_labels if s is not None}):
        idxs = [i for i, s in enumerate(sub_labels) if s == sub]
        correct = sum(1 for i in idxs if y_pred[i] == "DEFECT")
        recall_by_sub[sub] = correct / len(idxs)

    sorted_latencies = sorted(latencies)
    latency_report = {
        "mean": sum(latencies) / len(latencies) if latencies else 0.0,
        "p50": _percentile(sorted_latencies, 0.50),
        "p95": _percentile(sorted_latencies, 0.95),
        "max": max(latencies) if latencies else 0.0,
    }

    return EvalReport(
        data_source=data_source,
        n_samples=len(samples),
        accuracy=accuracy,
        precision_defect=precision,
        recall_defect=recall,
        f1_defect=f1,
        confusion={"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        recall_by_sub_label=recall_by_sub,
        false_positive_ids=tuple(fp_ids),
        false_negative_ids=tuple(fn_ids),
        latency_ms=latency_report,
        uncertain_count=uncertain_count,
        uncertain_policy=uncertain_policy,
    )
