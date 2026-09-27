"""Synthetic "bottle cap" image generator (P1.2 test input; ADR-0010, docs/DATASET_SPEC.md).

Every result from this module must be treated as synthetic in any report (D-026): it lets
the rest of the pipeline (preprocessing, inference, decision, sim) be built and tested with
0 VND of hardware, but it proves nothing about accuracy on real products. It deliberately
mirrors the three self-made defect types chosen in docs/DATASET_SPEC.md section 2 — one
easy, one medium, one hard — so an evaluation report is not artificially flattering.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from msfc.core.errors import VisionError

CANVAS_SIZE = 128
_CAP_CENTER = (64, 64)
_CAP_RADIUS = 50
_STICKER_RADIUS = 12
_POSITION_JITTER_PX = 8

#: The three hand-made defect types from docs/DATASET_SPEC.md section 2, ordered easy to hard.
DEFECT_SUB_LABELS: tuple[str, ...] = ("MARK", "STICKER_MISSING", "SCRATCH")


@dataclass(frozen=True, slots=True)
class LabeledSample:
    """One synthetic (or, later, real) image plus its ground truth, for training/evaluation.

    ``session_id`` matches the "capture session" concept in docs/DATASET_SPEC.md section 6:
    train/val/test must be split by session, never by individual image, to avoid the model
    memorising incidental correlations from a single lighting/position setup.
    """

    image: np.ndarray
    label: str  # "GOOD" | "DEFECT"
    sub_label: str | None
    session_id: str


def _blank_canvas(rng: np.random.Generator) -> np.ndarray:
    """Dark, mildly noisy background — stands in for a matte conveyor belt under LED light."""
    return rng.integers(15, 30, size=(CANVAS_SIZE, CANVAS_SIZE, 3), dtype=np.uint8)


def _draw_cap(image: np.ndarray, rng: np.random.Generator) -> tuple[int, int]:
    dx = int(rng.integers(-_POSITION_JITTER_PX, _POSITION_JITTER_PX + 1))
    dy = int(rng.integers(-_POSITION_JITTER_PX, _POSITION_JITTER_PX + 1))
    center = (_CAP_CENTER[0] + dx, _CAP_CENTER[1] + dy)
    color = tuple(int(c) for c in rng.integers(150, 200, size=3))
    cv2.circle(image, center, _CAP_RADIUS, color, thickness=-1)
    return center


def generate_sample(
    rng: np.random.Generator, label: str, sub_label: str | None = None, *, moving: bool = False
) -> np.ndarray:
    """Render one synthetic sample.

    Args:
        rng: a ``numpy.random.default_rng(seed)`` instance — callers own reproducibility.
        label: ``"GOOD"`` or ``"DEFECT"``.
        sub_label: required (one of :data:`DEFECT_SUB_LABELS`) when ``label == "DEFECT"``;
            must be ``None`` for ``"GOOD"``.
        moving: apply a horizontal motion-blur kernel, simulating a frame captured while the
            belt is running (docs/DATASET_SPEC.md section 4, "(b) Động").

    Raises:
        VisionError: invalid ``label``/``sub_label`` combination.
    """
    if label not in ("GOOD", "DEFECT"):
        raise VisionError(f"label must be 'GOOD' or 'DEFECT', got {label!r}")
    if label == "GOOD" and sub_label is not None:
        raise VisionError("sub_label must be None when label='GOOD'")
    if label == "DEFECT" and sub_label not in DEFECT_SUB_LABELS:
        raise VisionError(f"sub_label must be one of {DEFECT_SUB_LABELS} when label='DEFECT', got {sub_label!r}")

    image = _blank_canvas(rng)
    center = _draw_cap(image, rng)
    has_sticker = True

    if sub_label == "MARK":
        # High-contrast diagonal mark: the "easy" defect (large, dark, unambiguous).
        p1 = (center[0] - 20, center[1] - 20)
        p2 = (center[0] + 20, center[1] + 20)
        cv2.line(image, p1, p2, (10, 10, 10), thickness=4)
    elif sub_label == "STICKER_MISSING":
        # Structural absence: the "medium" defect (GOOD always has the inner sticker).
        has_sticker = False
    elif sub_label == "SCRATCH":
        # Low-contrast thin line close to the cap's own colour: the "hard" defect, included
        # deliberately so an honest recall number (likely well below 100%) gets reported.
        cap_color = image[center[1], center[0]].astype(int)
        scratch_color = tuple(int(max(0, c - 15)) for c in cap_color)
        cv2.line(image, (center[0] - 25, center[1]), (center[0] + 25, center[1]), scratch_color, thickness=1)

    if has_sticker:
        cv2.circle(image, center, _STICKER_RADIUS, (230, 230, 230), thickness=-1)

    if moving:
        kernel_size = 7
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
        kernel[kernel_size // 2, :] = 1.0 / kernel_size
        image = cv2.filter2D(image, -1, kernel)

    noise = rng.normal(0, 3, size=image.shape)
    return np.clip(image.astype(np.int16) + noise.astype(np.int16), 0, 255).astype(np.uint8)


def generate_dataset(
    *, seed: int, n_good: int, n_defect_per_sub_label: int, session_id: str, moving: bool = False
) -> list[LabeledSample]:
    """Build a labeled synthetic dataset for one "capture session".

    Args:
        n_good: number of GOOD samples.
        n_defect_per_sub_label: number of DEFECT samples *per* entry in
            :data:`DEFECT_SUB_LABELS` (so total DEFECT count is ``3 * n_defect_per_sub_label``).
    """
    if n_good < 0 or n_defect_per_sub_label < 0:
        raise VisionError("n_good and n_defect_per_sub_label must be >= 0")
    rng = np.random.default_rng(seed)
    samples: list[LabeledSample] = []
    for _ in range(n_good):
        samples.append(LabeledSample(image=generate_sample(rng, "GOOD", moving=moving),
                                      label="GOOD", sub_label=None, session_id=session_id))
    for sub_label in DEFECT_SUB_LABELS:
        for _ in range(n_defect_per_sub_label):
            samples.append(LabeledSample(image=generate_sample(rng, "DEFECT", sub_label, moving=moving),
                                          label="DEFECT", sub_label=sub_label, session_id=session_id))
    rng.shuffle(samples)  # avoid accidental ordering effects (e.g. a model "counting" position)
    return samples
