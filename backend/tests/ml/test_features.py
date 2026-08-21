from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from app.ml.features import (
    FEATURE_NAMES,
    assert_strictly_before,
    build_inference_features,
    build_training_features,
)
from tests.ml.helpers import seed_ml_market


async def test_training_and_inference_features_are_strictly_pre_cutoff(session) -> None:
    universe = await seed_ml_market(session, 110)
    cutoff = date(2024, 4, 20)
    training = await build_training_features(
        session, universe, cutoff, forward_days=5, sample_stride=5
    )
    inference = await build_inference_features(session, universe, cutoff)

    assert training.values.shape[1] == len(FEATURE_NAMES)
    assert training.target_returns is not None
    assert max(training.feature_dates) < cutoff
    assert max(training.target_dates) < cutoff
    assert inference.values.shape == (2, len(FEATURE_NAMES))
    assert inference.symbols == universe
    assert all(value < cutoff for value in inference.feature_dates)
    assert np.isfinite(inference.values).all()


def test_structural_date_guard_rejects_cutoff_and_future_rows() -> None:
    cutoff = date(2025, 1, 30)
    with pytest.raises(ValueError, match="strictly before"):
        assert_strictly_before((cutoff,), cutoff)
    with pytest.raises(ValueError, match="strictly before"):
        assert_strictly_before((date(2025, 1, 1),), cutoff, (date(2025, 2, 1),))


async def test_feature_builder_validates_empty_short_and_invalid_windows(session) -> None:
    cutoff = date(2025, 1, 30)
    with pytest.raises(ValueError, match="empty"):
        assert_strictly_before((), cutoff)
    with pytest.raises(ValueError, match="must not be empty"):
        await build_inference_features(session, (), cutoff)
    universe = await seed_ml_market(session, 20)
    with pytest.raises(ValueError, match="forward_days"):
        await build_training_features(session, universe, cutoff, forward_days=0)
    with pytest.raises(ValueError, match="sample_stride"):
        await build_training_features(
            session, universe, cutoff, forward_days=5, sample_stride=0
        )
    with pytest.raises(ValueError, match="insufficient feature history"):
        await build_inference_features(session, universe, cutoff)
