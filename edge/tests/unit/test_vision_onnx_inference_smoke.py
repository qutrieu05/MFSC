"""Smoke tests for msfc.vision.onnx_backend (P1.3 CNN scaffold — decisions D-033/D-035).

Proves the second half of the chain test_vision_training_smoke.py doesn't cover:

    checkpoint -> ONNX export -> ONNX Runtime inference -> existing postprocess() -> DecisionEngine

using the exact, unmodified msfc.vision.postprocess and msfc.decision.DecisionEngine code
that ClassicCvBaseline already runs through — proving OnnxInferenceEngine is a drop-in
InferenceEngine, not a parallel path that merely looks compatible.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch", reason="training scaffold requires torch, which is optional")
pytest.importorskip("onnxruntime", reason="onnx_backend requires onnxruntime, which is optional")

from msfc.core.errors import VisionError
from msfc.decision import DecisionEngine
from msfc.domain import ModelInfo, RawVerdict, Verdict
from msfc.vision import RoiConfig, generate_dataset, preprocess
from msfc.vision.frame import Frame
from msfc.vision.inference import InferenceOutput
from msfc.vision.onnx_backend import OnnxInferenceEngine
from msfc.vision.postprocess import Thresholds, postprocess
from msfc.vision.training import TrainingConfig, export_onnx, load_checkpoint, train_smoke_test

ROI = RoiConfig(x=0, y=0, width=128, height=128, target_size=(48, 48))


def _three_session_dataset():
    sessions = []
    for i, sid in enumerate(("s01", "s02", "s03")):
        sessions += generate_dataset(seed=i, n_good=6, n_defect_per_sub_label=2, session_id=sid)
    return sessions


@pytest.fixture(scope="module")
def onnx_engine(tmp_path_factory: pytest.TempPathFactory) -> OnnxInferenceEngine:
    """Train once per module (not per test) — this is a smoke test, not a benchmark, and
    re-training for every assertion would just burn CPU time for no extra coverage."""
    checkpoint_dir = tmp_path_factory.mktemp("checkpoint")
    onnx_path = tmp_path_factory.mktemp("onnx") / "tiny_cap_cnn.onnx"

    samples = _three_session_dataset()
    result = train_smoke_test(samples, roi=ROI, config=TrainingConfig(epochs=2, batch_size=4, seed=0),
                               checkpoint_dir=checkpoint_dir)
    model, roi = load_checkpoint(result.checkpoint_path)
    export_onnx(model, roi=roi, onnx_path=onnx_path)
    return OnnxInferenceEngine(onnx_path, name="tiny_cap_cnn", version="smoke-test-1")


def _sample_image() -> np.ndarray:
    sample = generate_dataset(seed=99, n_good=1, n_defect_per_sub_label=0, session_id="probe")[0]
    frame = Frame(image=sample.image, seq=0, captured_mono_ms=0, source="probe")
    return preprocess(frame, ROI)


# --------------------------------------------------------------------------- construction
def test_onnx_engine_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(VisionError, match="not found"):
        OnnxInferenceEngine(tmp_path / "missing.onnx", name="x", version="1")


# --------------------------------------------------------------------------- predict()
def test_onnx_engine_predict_returns_valid_inference_output(onnx_engine: OnnxInferenceEngine) -> None:
    output = onnx_engine.predict(_sample_image())
    assert isinstance(output, InferenceOutput)
    assert set(output.class_scores) == {"GOOD", "DEFECT"}
    assert output.class_scores["GOOD"] + output.class_scores["DEFECT"] == pytest.approx(1.0, abs=1e-5)
    assert 0.0 <= output.class_scores["DEFECT"] <= 1.0
    assert "inference" in output.timings_ms


def test_onnx_engine_rejects_wrong_shaped_image(onnx_engine: OnnxInferenceEngine) -> None:
    with pytest.raises(VisionError, match="HxWx3"):
        onnx_engine.predict(np.zeros((10, 10), dtype=np.uint8))


# --------------------------------------------------------------------------- end-to-end pipeline
def test_onnx_engine_plugs_into_existing_postprocess_and_decision_engine(
    onnx_engine: OnnxInferenceEngine,
) -> None:
    """The actual point of P1.3: swap ClassicCvBaseline for OnnxInferenceEngine and nothing
    downstream (postprocess/DecisionEngine) needs to change (ADR-0010's interchangeability)."""
    frame = Frame(image=_sample_image(), seq=1, captured_mono_ms=1_000, source="probe")
    output = onnx_engine.predict(frame.image)

    product_id = "7-1"  # <boot_id>-<counter>, per msfc.domain._validators.product_id
    model_info = ModelInfo(name=onnx_engine.name, version=onnx_engine.version, backend="onnxruntime")
    inspection = postprocess(output, Thresholds(), product_id=product_id, model=model_info, frame=frame)

    assert inspection.product_id == product_id
    assert inspection.verdict in (RawVerdict.GOOD, RawVerdict.DEFECT, RawVerdict.UNCERTAIN)
    assert inspection.class_scores == output.class_scores

    decision = DecisionEngine().decide(product_id, [inspection], detected_at_mono_ms=1_000, now_mono_ms=1_050)
    assert decision.final_verdict in (Verdict.GOOD, Verdict.DEFECT)
    assert decision.inputs[onnx_engine.name]["verdict"] == inspection.verdict.value


def test_onnx_output_matches_pytorch_model_on_the_same_input(onnx_engine: OnnxInferenceEngine, tmp_path: Path) -> None:
    """Cross-check against the exported checkpoint directly (not just "it runs") — regression
    guard for the export step itself (dynamo=False path; see training.export_onnx's docstring)."""
    samples = _three_session_dataset()
    result = train_smoke_test(samples, roi=ROI, config=TrainingConfig(epochs=1, batch_size=4, seed=0),
                               checkpoint_dir=tmp_path / "ckpt")
    model, roi = load_checkpoint(result.checkpoint_path)
    onnx_path = export_onnx(model, roi=roi, onnx_path=tmp_path / "cross_check.onnx")
    engine = OnnxInferenceEngine(onnx_path, name="cross-check", version="1")

    image = _sample_image()
    onnx_output = engine.predict(image)

    tensor = torch.from_numpy(image.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
    with torch.no_grad():
        torch_probs = torch.softmax(model(tensor), dim=1)[0].numpy()

    assert onnx_output.class_scores["GOOD"] == pytest.approx(float(torch_probs[0]), abs=1e-4)
    assert onnx_output.class_scores["DEFECT"] == pytest.approx(float(torch_probs[1]), abs=1e-4)
