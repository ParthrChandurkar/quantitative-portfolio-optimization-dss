"""Isolation-Forest detection over the existing AI Phase 1 feature vectors."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.templates import stock_anomaly_message
from app.alerts.types import Alert, AlertSeverity, AlertType
from app.ml.features import (
    FEATURE_NAMES,
    build_inference_features,
    build_training_features,
)

FloatMatrix = NDArray[np.float64]

# Two percent contamination treats anomalies as rare. The Isolation Forest decision
# boundary is zero; negating decision_function makes larger values more anomalous.
ISOLATION_CONTAMINATION = 0.02
ANOMALY_SCORE_THRESHOLD = 0.0
MIN_TRAINING_ROWS = 50
ISOLATION_TREES = 200
RANDOM_STATE = 42
# Weekly sampling preserves long regime history while avoiding redundant adjacent-day
# fits in a synchronous post-solve hook.
ANOMALY_SAMPLE_STRIDE = 5


@dataclass(frozen=True, slots=True)
class AnomalyScore:
    anomaly_score: float
    is_anomaly: bool


def score_latest_feature(
    historical_features: FloatMatrix,
    latest_feature: FloatMatrix,
) -> AnomalyScore:
    if historical_features.ndim != 2 or latest_feature.shape != (
        1,
        historical_features.shape[1],
    ):
        raise ValueError(
            "latest feature must be one row with the historical feature schema"
        )
    if historical_features.shape[0] < MIN_TRAINING_ROWS:
        raise ValueError(
            f"at least {MIN_TRAINING_ROWS} historical feature rows are required"
        )
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    training = imputer.fit_transform(historical_features)
    latest = imputer.transform(latest_feature)
    model = IsolationForest(
        n_estimators=ISOLATION_TREES,
        contamination=ISOLATION_CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    model.fit(training)
    score = -float(model.decision_function(latest)[0])
    return AnomalyScore(score, score > ANOMALY_SCORE_THRESHOLD)


async def detect_stock_anomalies(
    session: AsyncSession,
    holdings: tuple[tuple[uuid.UUID, str], ...],
    as_of_date: date,
    snapshot_id: uuid.UUID,
) -> list[Alert]:
    if not holdings:
        return []
    symbols = tuple(symbol for _, symbol in holdings)
    try:
        inference = await build_inference_features(session, symbols, as_of_date)
        training = await build_training_features(
            session,
            symbols,
            min(inference.feature_dates),
            forward_days=1,
            sample_stride=ANOMALY_SAMPLE_STRIDE,
        )
    except ValueError:
        return []
    alerts: list[Alert] = []
    for index, (stock_id, symbol) in enumerate(holdings):
        feature_date = inference.feature_dates[index]
        symbol_mask = np.asarray(training.symbols) == symbol
        historical = training.values[symbol_mask]
        try:
            result = score_latest_feature(
                historical, inference.values[index : index + 1]
            )
        except ValueError:
            continue
        if not result.is_anomaly:
            continue
        grounding = {
            "symbol": symbol,
            "anomaly_score": result.anomaly_score,
            "decision_threshold": ANOMALY_SCORE_THRESHOLD,
            "feature_date": feature_date.isoformat(),
            "feature_names": list(FEATURE_NAMES),
            "feature_vector": inference.values[index].tolist(),
            "training_row_count": int(historical.shape[0]),
        }
        alerts.append(
            Alert(
                AlertType.STOCK_ANOMALY,
                AlertSeverity.WARNING,
                stock_anomaly_message(grounding),
                grounding,
                snapshot_id=snapshot_id,
                stock_id=stock_id,
            )
        )
    return alerts
