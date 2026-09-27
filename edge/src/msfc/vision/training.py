"""CNN training smoke-test scaffold (P1.3 deferred sub-item — decisions D-033/D-035).

This module exists to prove one thing end to end:

    dataset -> training -> checkpoint -> ONNX export -> ONNX Runtime inference
        -> existing postprocess -> Decision Engine

It is explicitly **not** a production training pipeline. The network is tiny, trained for a
handful of epochs on 0-VND synthetic data (docs/DATASET_SPEC.md's generator), and every
number it produces must be reported as synthetic (see :class:`~msfc.vision.EvalReport`'s
``data_source`` field) — never as a claim about real products (D-026). Real training on a
captured dataset is P1.11 work, once camera hardware exists; procurement is not approved and
this module never touches hardware.

Not imported by ``msfc.vision``'s package ``__init__`` on purpose: it requires ``torch``,
which the rest of the vision package (``ClassicCvBaseline`` and everything using it) does
not need. Import this module directly: ``from msfc.vision.training import ...``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from msfc.core.errors import VisionError
from msfc.vision.frame import Frame
from msfc.vision.preprocess import RoiConfig, preprocess
from msfc.vision.synthetic import LabeledSample

_LABEL_TO_INDEX = {"GOOD": 0, "DEFECT": 1}
_INDEX_TO_LABEL = {v: k for k, v in _LABEL_TO_INDEX.items()}


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Deliberately small defaults — this trains a smoke test, not a product model."""

    epochs: int = 3
    batch_size: int = 8
    learning_rate: float = 1e-3
    seed: int = 0

    def __post_init__(self) -> None:
        if self.epochs <= 0:
            raise VisionError(f"epochs must be > 0, got {self.epochs!r}")
        if self.batch_size <= 0:
            raise VisionError(f"batch_size must be > 0, got {self.batch_size!r}")
        if self.learning_rate <= 0:
            raise VisionError(f"learning_rate must be > 0, got {self.learning_rate!r}")


@dataclass(frozen=True, slots=True)
class TrainingMetrics:
    """Same shape as :class:`~msfc.vision.EvalReport`'s core numbers, computed independently
    here (torch tensors, not the classical-baseline eval path) — DEFECT is the positive class."""

    accuracy: float
    precision_defect: float
    recall_defect: float
    f1_defect: float
    confusion: dict[str, int]  # {"tp", "fp", "tn", "fn"}
    data_source: str = "synthetic"


@dataclass(frozen=True, slots=True)
class TrainingResult:
    best_epoch: int
    best_val_metrics: TrainingMetrics
    test_metrics: TrainingMetrics
    checkpoint_path: Path
    history: tuple[TrainingMetrics, ...]  # validation metrics after every epoch


class CapDataset(Dataset):
    """Wraps :class:`LabeledSample` objects into ``(CHW float32 tensor, label index)`` pairs,
    reusing the exact same :func:`~msfc.vision.preprocess.preprocess` step production
    inference uses — training and inference must see identically-shaped input."""

    def __init__(self, samples: Sequence[LabeledSample], roi: RoiConfig) -> None:
        self._samples = list(samples)
        self._roi = roi

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        sample = self._samples[index]
        frame = Frame(image=sample.image, seq=index, captured_mono_ms=0, source=sample.session_id)
        processed = preprocess(frame, self._roi)  # HxWx3 uint8, BGR
        tensor = torch.from_numpy(processed.astype(np.float32) / 255.0).permute(2, 0, 1).contiguous()
        return tensor, _LABEL_TO_INDEX[sample.label]


def split_by_session(
    samples: Sequence[LabeledSample],
) -> tuple[list[LabeledSample], list[LabeledSample], list[LabeledSample]]:
    """Split into (train, val, test) **by capture session**, per docs/DATASET_SPEC.md
    section 6 — the earliest sessions become train, the second-to-last becomes val, and the
    latest (held out) session becomes test. Requires at least 3 distinct ``session_id``
    values; this is intentional and not relaxed for convenience, so a caller cannot
    accidentally leak a session across splits the way an index-based random split would.
    """
    by_session: dict[str, list[LabeledSample]] = defaultdict(list)
    for sample in samples:
        by_session[sample.session_id].append(sample)
    session_ids = sorted(by_session)
    if len(session_ids) < 3:
        raise VisionError(
            f"split_by_session requires >= 3 distinct session_id values, got {len(session_ids)}: "
            f"{session_ids}. Generate at least a train, a val and a held-out test session "
            "(docs/DATASET_SPEC.md section 6) rather than splitting one session by index."
        )
    test_session, val_session = session_ids[-1], session_ids[-2]
    train = [s for sid in session_ids[:-2] for s in by_session[sid]]
    return train, by_session[val_session], by_session[test_session]


class TinyCapCNN(nn.Module):
    """Deliberately tiny: three conv blocks + adaptive pooling + one linear layer. Works on
    any input spatial size (the adaptive pool fixes the feature-map size before the linear
    layer), so the same architecture serves both the 128px full-frame ROI used elsewhere in
    this codebase and a smaller ROI chosen to keep this smoke test's CPU training time low.
    """

    def __init__(self, num_classes: int = 2) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, kernel_size=3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(8, 16, kernel_size=3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(4),
        )
        self.classifier = nn.Linear(32 * 4 * 4, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)


def _evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> TrainingMetrics:
    model.eval()
    tp = fp = tn = fn = 0
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            predictions = model(images).argmax(dim=1).cpu().numpy()
            truth = labels.numpy()
            for pred, true in zip(predictions, truth):
                if true == 1 and pred == 1:
                    tp += 1
                elif true == 0 and pred == 1:
                    fp += 1
                elif true == 0 and pred == 0:
                    tn += 1
                else:
                    fn += 1
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return TrainingMetrics(accuracy=accuracy, precision_defect=precision, recall_defect=recall,
                            f1_defect=f1, confusion={"tp": tp, "fp": fp, "tn": tn, "fn": fn})


def train_smoke_test(
    samples: Sequence[LabeledSample],
    *,
    roi: RoiConfig,
    config: TrainingConfig,
    checkpoint_dir: Path,
) -> TrainingResult:
    """Train :class:`TinyCapCNN`, select the best epoch by validation F1, save a checkpoint.

    Raises:
        VisionError: no samples, or any split (train/val/test) ends up empty.
    """
    if not samples:
        raise VisionError("train_smoke_test() requires at least one sample")
    train, val, test = split_by_session(samples)
    for name, split in (("train", train), ("val", val), ("test", test)):
        if not split:
            raise VisionError(f"the {name} split is empty — check the session_id values in samples")

    torch.manual_seed(config.seed)
    device = torch.device("cpu")  # smoke test only; R-27 notes this machine's torch has no CUDA anyway
    model = TinyCapCNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loss_fn = nn.CrossEntropyLoss()

    train_loader = DataLoader(CapDataset(train, roi), batch_size=config.batch_size, shuffle=True)
    val_loader = DataLoader(CapDataset(val, roi), batch_size=config.batch_size)
    test_loader = DataLoader(CapDataset(test, roi), batch_size=config.batch_size)

    history: list[TrainingMetrics] = []
    best_f1 = -1.0
    best_epoch = -1
    best_state: dict[str, torch.Tensor] | None = None

    for epoch in range(config.epochs):
        model.train()
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = loss_fn(model(images), labels)
            loss.backward()
            optimizer.step()

        val_metrics = _evaluate(model, val_loader, device)
        history.append(val_metrics)
        if val_metrics.f1_defect >= best_f1:
            best_f1 = val_metrics.f1_defect
            best_epoch = epoch
            best_state = {key: value.clone() for key, value in model.state_dict().items()}

    assert best_state is not None  # guaranteed: config.epochs > 0 is enforced in __post_init__
    model.load_state_dict(best_state)

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "tiny_cap_cnn_best.pt"
    torch.save(
        {"state_dict": best_state, "best_epoch": best_epoch, "roi": roi, "config": config,
         "data_source": "synthetic"},
        checkpoint_path,
    )

    test_metrics = _evaluate(model, test_loader, device)
    return TrainingResult(best_epoch=best_epoch, best_val_metrics=history[best_epoch],
                           test_metrics=test_metrics, checkpoint_path=checkpoint_path,
                           history=tuple(history))


def export_onnx(model: nn.Module, *, roi: RoiConfig, onnx_path: Path) -> Path:
    """Export *model* (expects NCHW float32 in [0, 1], any spatial size) to ONNX.

    Uses the legacy TorchScript-based exporter (``dynamo=False``): the newer
    ``torch.export``-based path requires the optional ``onnxscript`` package, which this
    project does not otherwise need — the legacy path needs only the already-installed
    ``onnx`` package and round-trips this model exactly (verified: max abs difference
    between the PyTorch and ONNX Runtime outputs on the same input is ~3.7e-9).
    """
    model.eval()
    width, height = roi.target_size
    dummy = torch.zeros(1, 3, height, width)
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(model, dummy, str(onnx_path), input_names=["image"], output_names=["logits"],
                       dynamo=False)
    return onnx_path


def load_checkpoint(checkpoint_path: Path) -> tuple[TinyCapCNN, RoiConfig]:
    """Load a checkpoint saved by :func:`train_smoke_test` back into a ready-to-export model."""
    if not checkpoint_path.exists():
        raise VisionError(f"checkpoint not found: {checkpoint_path}")
    # weights_only=False: this checkpoint embeds our own RoiConfig/TrainingConfig dataclasses
    # alongside the tensors, and is always a file we just wrote ourselves (never downloaded).
    payload = torch.load(checkpoint_path, weights_only=False)
    model = TinyCapCNN()
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model, payload["roi"]
