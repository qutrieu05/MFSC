"""FrameSource implementations (P1.2): synthetic, image folder, video file, USB camera.

Only :class:`SyntheticFrameSource` is exercised end-to-end without any hardware.
:class:`ImageFolderFrameSource` and :class:`VideoFileFrameSource` are tested with real
(tiny, generated) files. :class:`UsbCameraFrameSource` cannot be exercised on its success
path until a camera exists (docs/HARDWARE_INVENTORY.md: hardware = NONE) — only its
failure path (no such device) is portable enough to test automatically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from msfc.core.errors import VisionError
from msfc.vision.frame import Frame
from msfc.vision.synthetic import DEFECT_SUB_LABELS, LabeledSample, generate_sample


class SyntheticFrameSource:
    """Feeds the pipeline from generated images — the "test input" required before any
    camera exists.

    Two modes:

    * ``sequence`` given: replays exactly those labeled samples, in order (deterministic —
      use this for evaluation and for integration tests that assert specific routing).
    * ``sequence=None``: generates an unbounded random stream (~15% DEFECT, uniform over
      :data:`~msfc.vision.synthetic.DEFECT_SUB_LABELS`) — use this for a "camera is always
      producing frames" style demo/soak run.
    """

    def __init__(
        self,
        *,
        sequence: Sequence[LabeledSample] | None = None,
        seed: int = 0,
        frame_interval_ms: int = 33,
        loop: bool = True,
        defect_rate: float = 0.15,
    ) -> None:
        if not (0.0 <= defect_rate <= 1.0):
            raise VisionError(f"defect_rate must be in [0, 1], got {defect_rate!r}")
        self._rng = np.random.default_rng(seed)
        self._sequence = list(sequence) if sequence is not None else None
        self._defect_rate = defect_rate
        self._index = 0
        self._seq = 0
        self._mono_ms = 0
        self._interval = frame_interval_ms
        self._loop = loop
        self._closed = False
        self._last_ground_truth: LabeledSample | None = None

    def read(self) -> Frame | None:
        if self._closed:
            raise VisionError("read() called on a closed SyntheticFrameSource")

        sample = self._next_sample()
        if sample is None:
            return None
        self._last_ground_truth = sample

        frame = Frame(image=sample.image, seq=self._seq, captured_mono_ms=self._mono_ms, source="synthetic")
        self._seq += 1
        self._mono_ms += self._interval
        return frame

    def _next_sample(self) -> LabeledSample | None:
        if self._sequence is not None:
            if self._index >= len(self._sequence):
                if not self._loop:
                    return None
                self._index = 0
            sample = self._sequence[self._index]
            self._index += 1
            return sample

        if self._rng.random() < self._defect_rate:
            sub_label = str(self._rng.choice(DEFECT_SUB_LABELS))
            image = generate_sample(self._rng, "DEFECT", sub_label)
            return LabeledSample(image=image, label="DEFECT", sub_label=sub_label, session_id="live")
        image = generate_sample(self._rng, "GOOD")
        return LabeledSample(image=image, label="GOOD", sub_label=None, session_id="live")

    @property
    def last_ground_truth(self) -> LabeledSample | None:
        """Test/evaluation-only: label of the most recently read frame.

        A real camera has no equivalent property — do not depend on this outside tests,
        the evaluation harness, or the P1.6 simulator's own bookkeeping.
        """
        return self._last_ground_truth

    def close(self) -> None:
        self._closed = True


class ImageFolderFrameSource:
    """Reads image files from a directory in sorted filename order (FR-VIS-01 test input)."""

    _EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp")

    def __init__(self, directory: Path, *, frame_interval_ms: int = 33, loop: bool = False) -> None:
        directory = Path(directory)
        if not directory.is_dir():
            raise VisionError(f"not a directory: {directory}")
        self._paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in self._EXTENSIONS)
        if not self._paths:
            raise VisionError(f"no images with extensions {self._EXTENSIONS} found in {directory}")
        self._interval = frame_interval_ms
        self._loop = loop
        self._index = 0
        self._seq = 0
        self._mono_ms = 0
        self._closed = False

    def read(self) -> Frame | None:
        if self._closed:
            raise VisionError("read() called on a closed ImageFolderFrameSource")
        if self._index >= len(self._paths):
            if not self._loop:
                return None
            self._index = 0

        path = self._paths[self._index]
        self._index += 1
        image = cv2.imread(str(path))
        if image is None:
            raise VisionError(f"failed to decode image: {path}")

        frame = Frame(image=image, seq=self._seq, captured_mono_ms=self._mono_ms, source=f"folder:{path.name}")
        self._seq += 1
        self._mono_ms += self._interval
        return frame

    def close(self) -> None:
        self._closed = True


class VideoFileFrameSource:
    """Reads frames from a video file via OpenCV (useful once real footage exists)."""

    def __init__(self, path: Path, *, loop: bool = False) -> None:
        self._path = Path(path)
        if not self._path.exists():
            raise VisionError(f"video file not found: {self._path}")
        self._cap = cv2.VideoCapture(str(self._path))
        if not self._cap.isOpened():
            raise VisionError(f"failed to open video file: {self._path}")
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._interval_ms = int(1000 / fps) if fps and fps > 0 else 33
        self._loop = loop
        self._seq = 0
        self._mono_ms = 0
        self._closed = False

    def read(self) -> Frame | None:
        if self._closed:
            raise VisionError("read() called on a closed VideoFileFrameSource")
        ok, image = self._cap.read()
        if not ok:
            if self._loop:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, image = self._cap.read()
            if not ok:
                return None

        frame = Frame(image=image, seq=self._seq, captured_mono_ms=self._mono_ms,
                       source=f"video:{self._path.name}")
        self._seq += 1
        self._mono_ms += self._interval_ms
        return frame

    def close(self) -> None:
        if not self._closed:
            self._cap.release()
            self._closed = True


class UsbCameraFrameSource:
    """Reads frames from a live USB camera (docs/HARDWARE_INTERFACE.md).

    Not exercised by automated tests beyond the "no such device" failure path — there is no
    camera in this environment (docs/HARDWARE_INVENTORY.md: hardware = NONE). Validating the
    success path is P1.11 work, once a camera is purchased (wave W1).
    """

    def __init__(self, device_index: int = 0, *, backend: int | None = None) -> None:
        self._cap = cv2.VideoCapture(device_index, backend) if backend is not None else cv2.VideoCapture(device_index)
        if not self._cap.isOpened():
            raise VisionError(f"failed to open camera at index {device_index}")
        self._seq = 0
        self._closed = False

    def read(self) -> Frame | None:
        if self._closed:
            raise VisionError("read() called on a closed UsbCameraFrameSource")
        ok, image = self._cap.read()
        if not ok:
            raise VisionError("camera read failed (device disconnected?) — see FT-01")
        mono_ms = int(self._cap.get(cv2.CAP_PROP_POS_MSEC))
        frame = Frame(image=image, seq=self._seq, captured_mono_ms=mono_ms, source="usb_camera")
        self._seq += 1
        return frame

    def close(self) -> None:
        if not self._closed:
            self._cap.release()
            self._closed = True
