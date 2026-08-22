from datetime import date
from uuid import uuid4

import numpy as np
import pytest

from app.alerts.stock_anomaly_detector import (
    MIN_TRAINING_ROWS,
    AnomalyScore,
    detect_stock_anomalies,
    score_latest_feature,
)
from app.ml.features import FeatureDataset


def test_isolation_forest_flags_extreme_row_but_not_typical_row() -> None:
    random = np.random.default_rng(42)
    history = random.normal(0.0, 0.15, size=(300, 12))
    typical = np.zeros((1, 12))
    anomalous = np.full((1, 12), 8.0)
    assert score_latest_feature(history, typical).is_anomaly is False
    anomaly = score_latest_feature(history, anomalous)
    assert anomaly.is_anomaly is True
    assert anomaly.anomaly_score > 0.0


def test_detector_rejects_insufficient_or_incompatible_history() -> None:
    with pytest.raises(ValueError, match=str(MIN_TRAINING_ROWS)):
        score_latest_feature(np.zeros((10, 12)), np.zeros((1, 12)))
    with pytest.raises(ValueError, match="schema"):
        score_latest_feature(np.zeros((100, 12)), np.zeros((1, 11)))


async def test_database_adapter_emits_only_flagged_held_stock(monkeypatch) -> None:
    feature_date = date(2026, 1, 30)
    inference = FeatureDataset(
        ("NORMAL", "OUTLIER"),
        (feature_date, feature_date),
        np.asarray([[0.0] * 12, [8.0] * 12]),
    )
    training = FeatureDataset(
        ("NORMAL",) * 50 + ("OUTLIER",) * 50,
        tuple(date(2025, 1, 1) for _ in range(100)),
        np.zeros((100, 12)),
    )

    async def inference_features(*_args, **_kwargs):
        return inference

    async def training_features(*_args, **_kwargs):
        return training

    monkeypatch.setattr(
        "app.alerts.stock_anomaly_detector.build_inference_features",
        inference_features,
    )
    monkeypatch.setattr(
        "app.alerts.stock_anomaly_detector.build_training_features",
        training_features,
    )
    monkeypatch.setattr(
        "app.alerts.stock_anomaly_detector.score_latest_feature",
        lambda _history, latest: AnomalyScore(0.25, bool(latest[0, 0] > 1)),
    )
    normal_id, outlier_id, snapshot_id = uuid4(), uuid4(), uuid4()
    alerts = await detect_stock_anomalies(
        object(),
        ((normal_id, "NORMAL"), (outlier_id, "OUTLIER")),
        date(2026, 1, 31),
        snapshot_id,
    )
    assert len(alerts) == 1
    assert alerts[0].stock_id == outlier_id
    assert alerts[0].grounding["feature_vector"] == [8.0] * 12


async def test_database_adapter_skips_empty_holdings() -> None:
    assert await detect_stock_anomalies(object(), (), date(2026, 1, 31), uuid4()) == []
