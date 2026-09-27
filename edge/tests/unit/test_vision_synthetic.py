"""Tests for msfc.vision.synthetic (the P1.2/P1.3 synthetic dataset generator)."""

from __future__ import annotations

import numpy as np
import pytest

from msfc.core.errors import VisionError
from msfc.vision import DEFECT_SUB_LABELS, generate_dataset, generate_sample


def test_good_sample_has_the_expected_shape_and_dtype() -> None:
    rng = np.random.default_rng(0)
    image = generate_sample(rng, "GOOD")
    assert image.shape == (128, 128, 3)
    assert image.dtype == np.uint8


@pytest.mark.parametrize("sub_label", DEFECT_SUB_LABELS)
def test_defect_sample_for_every_sub_label(sub_label: str) -> None:
    rng = np.random.default_rng(1)
    image = generate_sample(rng, "DEFECT", sub_label)
    assert image.shape == (128, 128, 3)


def test_good_rejects_a_sub_label() -> None:
    with pytest.raises(VisionError, match="sub_label must be None"):
        generate_sample(np.random.default_rng(0), "GOOD", "MARK")


def test_defect_requires_a_known_sub_label() -> None:
    with pytest.raises(VisionError, match="sub_label must be one of"):
        generate_sample(np.random.default_rng(0), "DEFECT", "NOT_A_REAL_DEFECT")


def test_unknown_label_is_rejected() -> None:
    with pytest.raises(VisionError, match="label must be"):
        generate_sample(np.random.default_rng(0), "MAYBE")


def test_same_seed_is_reproducible() -> None:
    a = generate_sample(np.random.default_rng(42), "GOOD")
    b = generate_sample(np.random.default_rng(42), "GOOD")
    assert np.array_equal(a, b)


def test_mark_defect_is_visibly_different_from_good() -> None:
    """The 'easy' defect must actually be easy: clearly more different from a GOOD sample
    than two identically-seeded GOOD samples are from each other (the noise-only floor)."""
    noise_floor = np.abs(
        generate_sample(np.random.default_rng(7), "GOOD").astype(int)
        - generate_sample(np.random.default_rng(7), "GOOD").astype(int)
    ).mean()
    assert noise_floor == 0.0  # identical seed, no branching difference => byte-identical

    mark_diff = np.abs(
        generate_sample(np.random.default_rng(7), "GOOD").astype(int)
        - generate_sample(np.random.default_rng(7), "DEFECT", "MARK").astype(int)
    ).mean()
    assert mark_diff > noise_floor + 0.5


def test_moving_frame_differs_from_static_frame() -> None:
    rng_a = np.random.default_rng(3)
    static = generate_sample(rng_a, "GOOD", moving=False)
    rng_b = np.random.default_rng(3)
    moving = generate_sample(rng_b, "GOOD", moving=True)
    assert not np.array_equal(static, moving)


# --------------------------------------------------------------------------- generate_dataset
def test_generate_dataset_has_the_right_counts() -> None:
    samples = generate_dataset(seed=0, n_good=10, n_defect_per_sub_label=4, session_id="s01")
    assert len(samples) == 10 + 4 * len(DEFECT_SUB_LABELS)
    assert sum(1 for s in samples if s.label == "GOOD") == 10
    for sub in DEFECT_SUB_LABELS:
        assert sum(1 for s in samples if s.sub_label == sub) == 4


def test_generate_dataset_tags_every_sample_with_the_session_id() -> None:
    samples = generate_dataset(seed=0, n_good=2, n_defect_per_sub_label=1, session_id="s07")
    assert all(s.session_id == "s07" for s in samples)


def test_generate_dataset_rejects_negative_counts() -> None:
    with pytest.raises(VisionError):
        generate_dataset(seed=0, n_good=-1, n_defect_per_sub_label=1, session_id="s01")


def test_generate_dataset_is_shuffled_not_grouped_by_label() -> None:
    """Construction order is GOOD-block-then-DEFECT-block; after a real shuffle, the first
    n_good slots should not still be exactly the GOOD block."""
    samples = generate_dataset(seed=1, n_good=20, n_defect_per_sub_label=20, session_id="s01")
    first_n_good_labels = [s.label for s in samples[:20]]
    assert not all(label == "GOOD" for label in first_n_good_labels)
