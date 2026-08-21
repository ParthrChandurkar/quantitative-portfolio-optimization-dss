"""Train and persist a leakage-safe gradient-boosting return forecaster."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MlForecastRun, Stock
from app.ml.features import (
    FeatureDataset,
    assert_strictly_before,
    build_training_features,
)

DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


@dataclass(frozen=True, slots=True)
class TrainingResult:
    artifact_path: Path
    estimation_end_date: date
    feature_importances: dict[str, float]
    training_row_count: int
    forward_days: int


def fit_forecast_model(
    dataset: FeatureDataset,
    estimation_end_date: date,
    *,
    forward_days: int = 21,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    random_state: int = 42,
) -> TrainingResult:
    """Fit one model after enforcing the temporal boundary on features and labels."""

    assert_strictly_before(
        dataset.feature_dates, estimation_end_date, dataset.target_dates
    )
    if dataset.target_returns is None:
        raise ValueError("training dataset requires target_returns")
    if dataset.values.ndim != 2 or dataset.values.shape[1] != len(
        dataset.feature_names
    ):
        raise ValueError("training feature matrix has an invalid shape")
    targets = np.asarray(dataset.target_returns, dtype=float)
    if targets.shape != (dataset.values.shape[0],) or not np.all(np.isfinite(targets)):
        raise ValueError("training targets must be finite and aligned")
    if len(targets) < 20:
        raise ValueError("at least 20 training rows are required")

    model = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    keep_empty_features=True,
                ),
            ),
            (
                "regressor",
                GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.05,
                    max_depth=3,
                    loss="huber",
                    random_state=random_state,
                ),
            ),
        ]
    )
    model.fit(dataset.values, targets)
    regressor = model.named_steps["regressor"]
    importances = {
        name: float(value)
        for name, value in zip(
            dataset.feature_names, regressor.feature_importances_, strict=True
        )
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / (
        f"return_forecast_{estimation_end_date.isoformat()}_N{forward_days}.joblib"
    )
    payload: dict[str, Any] = {
        "model": model,
        "estimation_end_date": estimation_end_date.isoformat(),
        "forward_days": forward_days,
        "feature_names": list(dataset.feature_names),
        "feature_importances": importances,
        "training_row_count": len(targets),
        "feature_date_min": min(dataset.feature_dates).isoformat(),
        "feature_date_max": max(dataset.feature_dates).isoformat(),
        "target_date_max": max(dataset.target_dates).isoformat(),
        "trained_at": datetime.now(UTC).isoformat(),
        "target_definition": f"forward {forward_days}-trading-day adjusted-close return",
        "return_annualization": f"prediction * {252 / forward_days:.12g}",
    }
    joblib.dump(payload, artifact_path)
    return TrainingResult(
        artifact_path,
        estimation_end_date,
        importances,
        len(targets),
        forward_days,
    )


async def train_forecast_model(
    session: AsyncSession,
    estimation_end_date: date,
    *,
    universe: tuple[str, ...] | None = None,
    forward_days: int = 21,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    random_state: int = 42,
) -> TrainingResult:
    """Build real database features, train the model, and store provenance."""

    selected = universe
    if selected is None:
        selected = tuple(
            (
                await session.scalars(select(Stock.symbol).order_by(Stock.symbol))
            ).all()
        )
    dataset = await build_training_features(
        session,
        selected,
        estimation_end_date,
        forward_days=forward_days,
        sample_stride=forward_days,
    )
    result = fit_forecast_model(
        dataset,
        estimation_end_date,
        forward_days=forward_days,
        artifact_dir=artifact_dir,
        random_state=random_state,
    )
    session.add(
        MlForecastRun(
            estimation_end_date=estimation_end_date,
            model_artifact_path=str(result.artifact_path),
            feature_importances=result.feature_importances,
            training_row_count=result.training_row_count,
        )
    )
    await session.commit()
    return result
