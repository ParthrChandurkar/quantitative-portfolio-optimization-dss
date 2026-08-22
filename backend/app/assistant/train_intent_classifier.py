"""Train an inspectable offline TF-IDF intent router."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.assistant.generate_training_data import DEFAULT_DATA_PATH
from app.assistant.intents import AssistantIntent, IntentPrediction

DEFAULT_ARTIFACT_PATH = (
    Path(__file__).resolve().parent / "artifacts" / "intent_classifier.joblib"
)


@dataclass(frozen=True, slots=True)
class IntentTrainingResult:
    train_accuracy: float
    test_accuracy: float
    labels: tuple[str, ...]
    confusion_matrix: tuple[tuple[int, ...], ...]
    training_rows: int
    test_rows: int
    artifact_path: Path


def load_training_data(path: Path = DEFAULT_DATA_PATH) -> tuple[list[str], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("assistant training CSV is empty")
    return [row["question"] for row in rows], [row["intent"] for row in rows]


def train_intent_classifier(
    data_path: Path = DEFAULT_DATA_PATH,
    artifact_path: Path = DEFAULT_ARTIFACT_PATH,
    *,
    random_state: int = 42,
) -> IntentTrainingResult:
    questions, intents = load_training_data(data_path)
    x_train, x_test, y_train, y_test = train_test_split(
        questions, intents, test_size=0.20, random_state=random_state, stratify=intents
    )
    model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True, ngram_range=(1, 2), sublinear_tf=True, min_df=2
                ),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=2_000, random_state=random_state),
            ),
        ]
    )
    model.fit(x_train, y_train)
    test_predictions = model.predict(x_test)
    labels = tuple(sorted(set(intents)))
    matrix = confusion_matrix(y_test, test_predictions, labels=labels)
    payload: dict[str, Any] = {
        "model": model,
        "labels": list(labels),
        "train_accuracy": float(accuracy_score(y_train, model.predict(x_train))),
        "test_accuracy": float(accuracy_score(y_test, test_predictions)),
        "confusion_matrix": matrix.tolist(),
        "training_rows": len(x_train),
        "test_rows": len(x_test),
        "training_source": "hand-authored seeds plus transparent template augmentation",
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, artifact_path)
    return IntentTrainingResult(
        payload["train_accuracy"],
        payload["test_accuracy"],
        labels,
        tuple(tuple(int(value) for value in row) for row in matrix),
        len(x_train),
        len(x_test),
        artifact_path,
    )


def classify_intent(
    question: str,
    artifact_path: Path = DEFAULT_ARTIFACT_PATH,
) -> IntentPrediction:
    artifact = joblib.load(artifact_path)
    model = artifact["model"]
    probabilities_array = model.predict_proba([question])[0]
    probabilities = {
        str(label): float(probability)
        for label, probability in zip(model.classes_, probabilities_array, strict=True)
    }
    label = str(model.predict([question])[0])
    return IntentPrediction(AssistantIntent(label), probabilities[label], probabilities)


if __name__ == "__main__":
    print(train_intent_classifier())
