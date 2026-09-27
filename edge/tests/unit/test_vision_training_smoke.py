"""Smoke tests for msfc.vision.training (P1.3 CNN scaffold — decisions D-033/D-035).

Keeps everything deliberately tiny (few epochs, small dataset, small ROI) so this runs in a
few seconds on CPU. These tests prove the *pipeline* dataset->training->checkpoint works —
they explicitly do NOT assert any accuracy threshold, because docs/RISK_REGISTER.md R-28
already documents that separating GOOD from DEFECT on this synthetic generator is hard even
for a calibrated classical baseline; asserting "the CNN must get > X% accuracy" here would
either be a flaky test or, worse, an invitation to quietly loosen it until it always passes.
See test_vision_onnx_inference_smoke.py for what happens after training.
"""

from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch", reason="training scaffold requires torch, which is optional")

from msfc.core.errors import VisionError
from msfc.vision import RoiConfig, generate_dataset
from msfc.vision.training import (
    CapDataset,
    TinyCapCNN,
    TrainingConfig,
    TrainingResult,
    load_checkpoint,
    split_by_session,
    train_smoke_test,
)

ROI = RoiConfig(x=0, y=0, width=128, height=128, target_size=(48, 48))  # small: keeps CPU training fast


def _three_session_dataset():
    sessions = []
    for i, sid in enumerate(("s01", "s02", "s03")):
        sessions += generate_dataset(seed=i, n_good=6, n_defect_per_sub_label=2, session_id=sid)
    return sessions


# --------------------------------------------------------------------------- split_by_session
def test_split_by_session_assigns_earliest_to_train_and_last_to_test() -> None:
    samples = _three_session_dataset()
    train, val, test = split_by_session(samples)
    assert {s.session_id for s in train} == {"s01"}
    assert {s.session_id for s in val} == {"s02"}
    assert {s.session_id for s in test} == {"s03"}
    assert len(train) + len(val) + len(test) == len(samples)


def test_split_by_session_uses_more_than_the_last_two_sessions_for_train() -> None:
    samples = []
    for i, sid in enumerate(("s01", "s02", "s03", "s04")):
        samples += generate_dataset(seed=i, n_good=2, n_defect_per_sub_label=1, session_id=sid)
    train, val, test = split_by_session(samples)
    assert {s.session_id for s in train} == {"s01", "s02"}
    assert {s.session_id for s in val} == {"s03"}
    assert {s.session_id for s in test} == {"s04"}


def test_split_by_session_rejects_fewer_than_three_sessions() -> None:
    samples = generate_dataset(seed=0, n_good=2, n_defect_per_sub_label=1, session_id="only_one")
    with pytest.raises(VisionError, match="3 distinct session_id"):
        split_by_session(samples)


# --------------------------------------------------------------------------- CapDataset / TinyCapCNN
def test_cap_dataset_returns_chw_float_tensor_and_label_index() -> None:
    samples = generate_dataset(seed=0, n_good=1, n_defect_per_sub_label=1, session_id="s")
    dataset = CapDataset(samples, ROI)
    tensor, label = dataset[0]
    assert tensor.shape == (3, 48, 48)
    assert tensor.dtype == torch.float32
    assert 0.0 <= tensor.min() and tensor.max() <= 1.0
    assert label in (0, 1)


def test_tiny_cnn_forward_pass_produces_two_logits() -> None:
    model = TinyCapCNN()
    dummy = torch.zeros(2, 3, 48, 48)
    output = model(dummy)
    assert output.shape == (2, 2)


def test_tiny_cnn_accepts_a_different_spatial_size() -> None:
    """The adaptive pool makes the architecture size-agnostic — important since the real
    ROI elsewhere in the pipeline is 128x128, not this test's smaller 48x48."""
    model = TinyCapCNN()
    output = model(torch.zeros(1, 3, 128, 128))
    assert output.shape == (1, 2)


# --------------------------------------------------------------------------- train_smoke_test
def test_training_config_validation() -> None:
    with pytest.raises(VisionError, match="epochs"):
        TrainingConfig(epochs=0)
    with pytest.raises(VisionError, match="batch_size"):
        TrainingConfig(batch_size=0)
    with pytest.raises(VisionError, match="learning_rate"):
        TrainingConfig(learning_rate=0)


def test_train_smoke_test_rejects_empty_samples(tmp_path: Path) -> None:
    with pytest.raises(VisionError, match="at least one sample"):
        train_smoke_test([], roi=ROI, config=TrainingConfig(epochs=1), checkpoint_dir=tmp_path)


def test_train_smoke_test_runs_end_to_end_and_saves_a_checkpoint(tmp_path: Path) -> None:
    samples = _three_session_dataset()
    result = train_smoke_test(samples, roi=ROI, config=TrainingConfig(epochs=2, batch_size=4, seed=0),
                               checkpoint_dir=tmp_path)

    assert isinstance(result, TrainingResult)
    assert result.checkpoint_path.exists()
    assert result.checkpoint_path == tmp_path / "tiny_cap_cnn_best.pt"
    assert 0 <= result.best_epoch < 2
    assert len(result.history) == 2
    for metrics in (*result.history, result.test_metrics):
        assert metrics.data_source == "synthetic"
        assert sum(metrics.confusion.values()) > 0
        assert 0.0 <= metrics.accuracy <= 1.0


def test_train_smoke_test_is_reproducible_with_the_same_seed(tmp_path: Path) -> None:
    samples = _three_session_dataset()
    config = TrainingConfig(epochs=1, batch_size=4, seed=42)
    r1 = train_smoke_test(samples, roi=ROI, config=config, checkpoint_dir=tmp_path / "a")
    r2 = train_smoke_test(samples, roi=ROI, config=config, checkpoint_dir=tmp_path / "b")
    assert r1.test_metrics.confusion == r2.test_metrics.confusion


def test_load_checkpoint_round_trips_a_working_model(tmp_path: Path) -> None:
    samples = _three_session_dataset()
    result = train_smoke_test(samples, roi=ROI, config=TrainingConfig(epochs=1, batch_size=4),
                               checkpoint_dir=tmp_path)

    model, loaded_roi = load_checkpoint(result.checkpoint_path)
    assert loaded_roi == ROI
    model.eval()
    with torch.no_grad():
        output = model(torch.zeros(1, 3, 48, 48))
    assert output.shape == (1, 2)


def test_load_checkpoint_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(VisionError, match="not found"):
        load_checkpoint(tmp_path / "does_not_exist.pt")
