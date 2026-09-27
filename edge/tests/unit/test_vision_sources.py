"""Tests for msfc.vision.sources — all four FrameSource implementations.

ImageFolderFrameSource and VideoFileFrameSource are tested against real (tiny, generated)
files, proving the OpenCV read path genuinely works, not just the plumbing around it.
UsbCameraFrameSource only has its failure path tested (no camera in this environment —
docs/HARDWARE_INVENTORY.md: hardware = NONE); the success path is P1.11 work.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from msfc.core.errors import VisionError
from msfc.vision import ImageFolderFrameSource, LabeledSample, SyntheticFrameSource, UsbCameraFrameSource
from msfc.vision import VideoFileFrameSource, generate_sample


# --------------------------------------------------------------------------- SyntheticFrameSource
def test_synthetic_source_default_stream_produces_increasing_seq_and_time() -> None:
    source = SyntheticFrameSource(seed=0, frame_interval_ms=10)
    f0 = source.read()
    f1 = source.read()
    assert f0.seq == 0 and f1.seq == 1
    assert f1.captured_mono_ms - f0.captured_mono_ms == 10
    assert f0.source == "synthetic"


def test_synthetic_source_tracks_ground_truth_of_last_frame() -> None:
    source = SyntheticFrameSource(seed=0)
    source.read()
    truth = source.last_ground_truth
    assert isinstance(truth, LabeledSample)
    assert truth.label in ("GOOD", "DEFECT")


def test_synthetic_source_replays_an_explicit_sequence_in_order() -> None:
    rng = np.random.default_rng(0)
    seq = [
        LabeledSample(image=generate_sample(rng, "GOOD"), label="GOOD", sub_label=None, session_id="s"),
        LabeledSample(image=generate_sample(rng, "DEFECT", "MARK"), label="DEFECT", sub_label="MARK", session_id="s"),
    ]
    source = SyntheticFrameSource(sequence=seq, loop=False)
    assert source.read() is not None and source.last_ground_truth.label == "GOOD"
    assert source.read() is not None and source.last_ground_truth.label == "DEFECT"
    assert source.read() is None  # exhausted, loop=False


def test_synthetic_source_loops_the_sequence() -> None:
    rng = np.random.default_rng(0)
    seq = [LabeledSample(image=generate_sample(rng, "GOOD"), label="GOOD", sub_label=None, session_id="s")]
    source = SyntheticFrameSource(sequence=seq, loop=True)
    for _ in range(5):
        assert source.read() is not None


def test_synthetic_source_rejects_bad_defect_rate() -> None:
    with pytest.raises(VisionError, match="defect_rate"):
        SyntheticFrameSource(defect_rate=1.5)


def test_synthetic_source_read_after_close_raises() -> None:
    source = SyntheticFrameSource(seed=0)
    source.close()
    with pytest.raises(VisionError, match="closed"):
        source.read()


# --------------------------------------------------------------------------- ImageFolderFrameSource
def _write_png(path: Path, value: int) -> None:
    image = np.full((32, 32, 3), value, dtype=np.uint8)
    ok = cv2.imwrite(str(path), image)
    assert ok, f"cv2.imwrite failed for {path}"


def test_image_folder_source_reads_files_in_sorted_order(tmp_path: Path) -> None:
    _write_png(tmp_path / "b.png", 200)
    _write_png(tmp_path / "a.png", 100)

    source = ImageFolderFrameSource(tmp_path, frame_interval_ms=5)
    first = source.read()
    second = source.read()
    assert first.image[0, 0, 0] == 100  # a.png sorts before b.png
    assert second.image[0, 0, 0] == 200
    assert second.captured_mono_ms - first.captured_mono_ms == 5
    assert source.read() is None  # loop=False by default


def test_image_folder_source_can_loop(tmp_path: Path) -> None:
    _write_png(tmp_path / "a.png", 1)
    source = ImageFolderFrameSource(tmp_path, loop=True)
    for _ in range(4):
        assert source.read() is not None


def test_image_folder_source_empty_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(VisionError, match="no images"):
        ImageFolderFrameSource(tmp_path)


def test_image_folder_source_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(VisionError, match="not a directory"):
        ImageFolderFrameSource(tmp_path / "does-not-exist")


def test_image_folder_source_read_after_close_raises(tmp_path: Path) -> None:
    _write_png(tmp_path / "a.png", 1)
    source = ImageFolderFrameSource(tmp_path)
    source.close()
    with pytest.raises(VisionError, match="closed"):
        source.read()


# --------------------------------------------------------------------------- VideoFileFrameSource
@pytest.fixture()
def tiny_video(tmp_path: Path) -> Path:
    path = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (32, 32))
    assert writer.isOpened(), "cv2.VideoWriter failed to open — environment cannot write mp4"
    for i in range(5):
        writer.write(np.full((32, 32, 3), i * 10, dtype=np.uint8))
    writer.release()
    return path


def test_video_source_reads_every_frame(tiny_video: Path) -> None:
    source = VideoFileFrameSource(tiny_video)
    count = 0
    while source.read() is not None:
        count += 1
    assert count == 5


def test_video_source_frames_have_increasing_seq(tiny_video: Path) -> None:
    source = VideoFileFrameSource(tiny_video)
    seqs = []
    while (frame := source.read()) is not None:
        seqs.append(frame.seq)
    assert seqs == list(range(5))


def test_video_source_can_loop(tiny_video: Path) -> None:
    source = VideoFileFrameSource(tiny_video, loop=True)
    for _ in range(12):  # more than the 5 frames in the clip
        assert source.read() is not None


def test_video_source_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(VisionError, match="not found"):
        VideoFileFrameSource(tmp_path / "nope.mp4")


def test_video_source_read_after_close_raises(tiny_video: Path) -> None:
    source = VideoFileFrameSource(tiny_video)
    source.close()
    with pytest.raises(VisionError, match="closed"):
        source.read()
    source.close()  # idempotent


# --------------------------------------------------------------------------- UsbCameraFrameSource
def test_usb_camera_source_missing_device_raises() -> None:
    """No camera exists in this environment; a wildly out-of-range index must fail to open
    rather than silently returning black frames — this is the one thing about this class we
    can honestly test without hardware (docs/HARDWARE_INVENTORY.md: hardware = NONE)."""
    with pytest.raises(VisionError, match="failed to open camera"):
        UsbCameraFrameSource(device_index=99)
