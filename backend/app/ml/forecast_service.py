"""Load a temporally eligible model and produce an optimizer-shaped return vector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from numpy.typing import NDArray
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import FEATURE_NAMES, build_inference_features
from app.ml.train_forecast_model import DEFAULT_ARTIFACT_DIR
from app.optimization.data import TRADING_DAYS


@dataclass(frozen=True, slots=True)
class ForecastResult:
    symbols: tuple[str, ...]
    expected_returns: NDArray[np.float64]
    as_of_date: date
    feature_dates: tuple[date, ...]
    model_estimation_end_date: date
    model_artifact_path: Path
    forward_days: int


def _load_latest_eligible_artifact(
    artifact_dir: Path, as_of_date: date
) -> tuple[Path, dict[str, Any]]:
    eligible: list[tuple[date, Path, dict[str, Any]]] = []
    for path in artifact_dir.glob("return_forecast_*_N*.joblib"):
        payload = joblib.load(path)
        cutoff = date.fromisoformat(str(payload["estimation_end_date"]))
        # Artifact eligibility is itself strict, in addition to strict row filtering.
        if cutoff < as_of_date:
            eligible.append((cutoff, path, payload))
    if not eligible:
        raise FileNotFoundError(
            f"no ML forecast artifact trained before {as_of_date.isoformat()}"
        )
    _, path, payload = max(eligible, key=lambda item: (item[0], item[1].stat().st_mtime))
    return path, payload


async def get_ml_forecast(
    session: AsyncSession,
    universe: tuple[str, ...],
    as_of_date: date,
    *,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
) -> ForecastResult:
    """Return annualized ML mu aligned exactly with ``universe``."""

    path, artifact = _load_latest_eligible_artifact(artifact_dir, as_of_date)
    artifact_names = tuple(str(name) for name in artifact["feature_names"])
    if artifact_names != FEATURE_NAMES:
        raise ValueError("model artifact feature schema does not match the application")
    features = await build_inference_features(session, universe, as_of_date)
    model = artifact["model"]
    forward_days = int(artifact["forward_days"])
    forecast = np.asarray(model.predict(features.values), dtype=float)
    annualized = forecast * (TRADING_DAYS / forward_days)
    if annualized.shape != (len(universe),):
        raise ValueError("ML forecast is not aligned with the requested universe")
    if not np.all(np.isfinite(annualized)):
        raise ValueError("ML forecast contains NaN or infinite values")
    return ForecastResult(
        universe,
        annualized,
        as_of_date,
        features.feature_dates,
        date.fromisoformat(str(artifact["estimation_end_date"])),
        path,
        forward_days,
    )
