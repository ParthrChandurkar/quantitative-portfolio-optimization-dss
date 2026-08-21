from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from app.ml.features import FEATURE_NAMES, FeatureDataset
from app.ml.forecast_service import get_ml_forecast
from app.ml.train_forecast_model import fit_forecast_model
from tests.ml.helpers import seed_ml_market


async def test_forecast_matches_optimizer_mu_shape_and_is_finite(session, tmp_path) -> None:
    universe = await seed_ml_market(session, 100)
    model_cutoff = date(2024, 3, 1)
    rows = 30
    rng = np.random.default_rng(7)
    values = rng.normal(size=(rows, len(FEATURE_NAMES)))
    dates = tuple(model_cutoff - timedelta(days=rows - index) for index in range(rows))
    dataset = FeatureDataset(
        tuple("MLAAA" for _ in range(rows)),
        dates,
        values,
        FEATURE_NAMES,
        values[:, 0] * 0.01,
        dates,
    )
    fit_forecast_model(dataset, model_cutoff, artifact_dir=tmp_path)

    result = await get_ml_forecast(
        session, universe, date(2024, 4, 10), artifact_dir=tmp_path
    )
    assert result.symbols == universe
    assert result.expected_returns.shape == (len(universe),)
    assert np.isfinite(result.expected_returns).all()
    assert all(value < result.as_of_date for value in result.feature_dates)
    assert result.model_estimation_end_date < result.as_of_date


async def test_model_cutoff_must_be_strictly_before_forecast_date(session, tmp_path) -> None:
    universe = await seed_ml_market(session, 70)
    with pytest.raises(FileNotFoundError, match="no ML forecast artifact"):
        await get_ml_forecast(session, universe, date(2024, 3, 11), artifact_dir=tmp_path)
