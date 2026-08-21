from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from app.ml.features import FEATURE_NAMES, FeatureDataset
from app.ml.train_forecast_model import fit_forecast_model
from app.optimization.data import build_market_data
from tests.ml.helpers import seed_ml_market


async def test_historical_default_is_identical_and_ml_is_drop_in(session, tmp_path) -> None:
    universe = await seed_ml_market(session, 100)
    as_of = date(2024, 4, 10)
    implicit = await build_market_data(session, universe, as_of, 30)
    explicit = await build_market_data(
        session, universe, as_of, 30, "historical_mean"
    )
    assert np.array_equal(implicit.expected_returns, explicit.expected_returns)
    assert implicit.return_estimation_method == "historical_mean"

    cutoff = date(2024, 3, 1)
    rows = 30
    rng = np.random.default_rng(21)
    values = rng.normal(size=(rows, len(FEATURE_NAMES)))
    dates = tuple(cutoff - timedelta(days=rows - index) for index in range(rows))
    dataset = FeatureDataset(
        tuple("MLAAA" for _ in range(rows)),
        dates,
        values,
        FEATURE_NAMES,
        0.04 + values[:, 0] * 0.01,
        dates,
    )
    fit_forecast_model(dataset, cutoff, artifact_dir=tmp_path)
    ml = await build_market_data(
        session,
        universe,
        as_of,
        30,
        "ml_forecast",
        ml_artifact_dir=tmp_path,
    )
    assert ml.expected_returns.shape == implicit.expected_returns.shape
    assert np.isfinite(ml.expected_returns).all()
    assert not np.array_equal(ml.expected_returns, implicit.expected_returns)
    assert np.array_equal(ml.covariance, implicit.covariance)
    assert ml.return_estimation_method == "ml_forecast"
