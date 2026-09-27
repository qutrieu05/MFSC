"""The one type every FrameSource produces, and the interface itself (Layer 3, IF-03).

``msfc.vision`` depends only on ``msfc.core`` and ``msfc.domain`` (ARCHITECTURE.md section
7.2) — it has no idea MQTT exists. A camera, a folder of images, a video file and (later) a
live USB webcam are all just something with a ``.read()`` method that returns a
:class:`Frame` or ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True, slots=True)
class Frame:
    """One captured image plus the metadata needed to reason about timing (FR-VIS-01).

    ``image`` is HxWx3 ``uint8`` in BGR order (OpenCV's convention) — every source in this
    package produces that shape, so preprocessing code never has to branch on source type.
    """

    image: np.ndarray
    seq: int
    captured_mono_ms: int
    source: str


class FrameSource(Protocol):
    """What ``msfc.services`` (later) and every test in this package depend on.

    Implementations: :class:`~msfc.vision.sources.SyntheticFrameSource` (P1.2 test input),
    :class:`~msfc.vision.sources.ImageFolderFrameSource`,
    :class:`~msfc.vision.sources.VideoFileFrameSource`, and
    :class:`~msfc.vision.sources.UsbCameraFrameSource` (real hardware — see
    docs/HARDWARE_INTERFACE.md; not exercised by automated tests until a camera exists).
    """

    def read(self) -> Frame | None:
        """Return the next frame, or ``None`` when the source is exhausted (never blocks
        forever waiting for a frame that will not come — a live camera returns a fresh
        frame or raises, it does not return None while still open)."""

    def close(self) -> None:
        """Release any underlying resource. Idempotent."""
