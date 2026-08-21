from __future__ import annotations

from datetime import date, timedelta

import joblib
import numpy as np
import pytest

from app.ml.features import FEATURE_NAMES, FeatureDataset
from app.ml.train_forecast_model import fit_forecast_model, train_forecast_model
from tests.ml.helpers import seed_ml_market


def synthetic_dataset(cutoff: date, *, leaking: bool = False) -> FeatureDataset:
    rows = 30
    rng = np.random.default_rng(42)
    feature_dates = tuple(cutoff - timedelta(days=rows - index) for index in range(rows))
    if leaking:
        feature_dates = (*feature_dates[:-1], cutoff)
    values = rng.normal(size=(rows, len(FEATURE_NAMES)))
    targets = values[:, 0] * 0.02 - values[:, 7] * 0.01
    return FeatureDataset(
        tuple("MLAAA" for _ in range(rows)),
        feature_dates,
        values,
        FEATURE_NAMES,
        targets,
        feature_dates,
    )


def test_fit_saves_a_reproducible_artifact_and_importances(tmp_path) -> None:
    cutoff = date(2025, 1, 30)
    result = fit_forecast_model(synthetic_dataset(cutoff), cutoff, artifact_dir=tmp_path)
    artifact = joblib.load(result.artifact_path)

    assert result.training_row_count == 30
    assert set(result.feature_importances) == set(FEATURE_NAMES)
    assert artifact["estimation_end_date"] == cutoff.isoformat()
    assert artifact["target_date_max"] < cutoff.isoformat()


def test_training_rejects_any_feature_at_or_after_cutoff(tmp_path) -> None:
    cutoff = date(2025, 1, 30)
    with pytest.raises(ValueError, match="strictly before"):
        fit_forecast_model(
            synthetic_dataset(cutoff, leaking=True), cutoff, artifact_dir=tmp_path
        )


def test_training_validates_targets_shape_and_minimum_rows(tmp_path) -> None:
    cutoff = date(2025, 1, 30)
    valid = synthetic_dataset(cutoff)
    without_targets = FeatureDataset(
        valid.symbols, valid.feature_dates, valid.values, valid.feature_names
    )
    with pytest.raises(ValueError, match="target_returns"):
        fit_forecast_model(without_targets, cutoff, artifact_dir=tmp_path)
    invalid_shape = FeatureDataset(
        valid.symbols,
        valid.feature_dates,
        valid.values[:, :-1],
        valid.feature_names,
        valid.target_returns,
        valid.target_dates,
    )
    with pytest.raises(ValueError, match="invalid shape"):
        fit_forecast_model(invalid_shape, cutoff, artifact_dir=tmp_path)
    too_small = FeatureDataset(
        valid.symbols[:10],
        valid.feature_dates[:10],
        valid.values[:10],
        valid.feature_names,
        valid.target_returns[:10],
        valid.target_dates[:10],
    )
    with pytest.raises(ValueError, match="at least 20"):
        fit_forecast_model(too_small, cutoff, artifact_dir=tmp_path)


async def test_database_training_persists_provenance(session, tmp_path) -> None:
    universe = await seed_ml_market(session, 180)
    result = await train_forecast_model(
        session,
        date(2024, 6, 29),
        universe=universe,
        forward_days=5,
        artifact_dir=tmp_path,
    )
    assert result.artifact_path.exists()
    assert result.training_row_count >= 20
