"""Train and compare inspectable classifiers against rubric-derived labels."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.personalization.generate_training_data import DEFAULT_DATA_PATH
from app.personalization.questionnaire import FEATURE_NAMES, answers_to_features

DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "risk_classifier.joblib"


@dataclass(frozen=True, slots=True)
class RiskClassifierTrainingResult:
    selected_model: str
    train_accuracy: float
    test_accuracy: float
    candidate_metrics: dict[str, dict[str, float]]
    feature_reasoning: dict[str, Any]
    training_rows: int
    test_rows: int
    artifact_path: Path


def load_training_csv(path: Path = DEFAULT_DATA_PATH) -> tuple[np.ndarray, np.ndarray]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("synthetic training CSV is empty")
    features = np.asarray(
        [
            answers_to_features({name: row[name] for name in FEATURE_NAMES})
            for row in rows
        ],
        dtype=float,
    )
    labels = np.asarray([row["label"] for row in rows], dtype=str)
    return features, labels


def train_risk_classifier(
    data_path: Path = DEFAULT_DATA_PATH,
    artifact_path: Path = DEFAULT_ARTIFACT_PATH,
    *,
    random_state: int = 42,
) -> RiskClassifierTrainingResult:
    features, labels = load_training_csv(data_path)
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.20,
        random_state=random_state,
        stratify=labels,
    )
    candidates = {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2_000, random_state=random_state),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=250,
            max_depth=12,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        ),
    }
    metrics: dict[str, dict[str, float]] = {}
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        metrics[name] = {
            "train_accuracy": float(accuracy_score(y_train, model.predict(x_train))),
            "test_accuracy": float(accuracy_score(y_test, model.predict(x_test))),
        }
    selected_name = max(
        candidates,
        key=lambda name: (metrics[name]["test_accuracy"], -metrics[name]["train_accuracy"]),
    )
    selected_model = candidates[selected_name]
    logistic = candidates["logistic_regression"].named_steps["logisticregression"]
    forest = candidates["random_forest"]
    candidate_reasoning: dict[str, dict[str, Any]] = {
        "logistic_regression": {
            "classes": logistic.classes_.tolist(),
            "coefficients": {
                category: dict(zip(FEATURE_NAMES, coefficients, strict=True))
                for category, coefficients in zip(
                    logistic.classes_, logistic.coef_, strict=True
                )
            },
        },
        "random_forest": {
            "feature_importances": dict(
                zip(FEATURE_NAMES, forest.feature_importances_, strict=True)
            )
        },
    }
    feature_reasoning = candidate_reasoning[selected_name]
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": selected_model,
        "selected_model": selected_name,
        "candidate_metrics": metrics,
        "feature_names": list(FEATURE_NAMES),
        "feature_reasoning": feature_reasoning,
        "candidate_feature_reasoning": candidate_reasoning,
        "training_rows": len(x_train),
        "test_rows": len(x_test),
        "label_source": "transparent weighted rubric; not observed investor outcomes",
    }
    joblib.dump(payload, artifact_path)
    return RiskClassifierTrainingResult(
        selected_name,
        metrics[selected_name]["train_accuracy"],
        metrics[selected_name]["test_accuracy"],
        metrics,
        feature_reasoning,
        len(x_train),
        len(x_test),
        artifact_path,
    )


if __name__ == "__main__":
    print(train_risk_classifier())
