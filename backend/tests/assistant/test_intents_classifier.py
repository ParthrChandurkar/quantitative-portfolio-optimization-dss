import joblib

from app.assistant.generate_training_data import generate_training_data
from app.assistant.intents import AssistantIntent
from app.assistant.train_intent_classifier import (
    classify_intent,
    train_intent_classifier,
)


def test_classifier_reports_accuracy_and_inspectable_confusion_matrix(tmp_path) -> None:
    data_path = generate_training_data(tmp_path / "questions.csv")
    artifact_path = tmp_path / "intent.joblib"
    result = train_intent_classifier(data_path, artifact_path)
    artifact = joblib.load(artifact_path)

    assert result.test_accuracy >= 0.85
    assert result.training_rows == 1_680
    assert result.test_rows == 420
    assert len(result.confusion_matrix) == len(AssistantIntent)
    assert all(len(row) == len(AssistantIntent) for row in result.confusion_matrix)
    assert artifact["confusion_matrix"] == [
        list(row) for row in result.confusion_matrix
    ]
    assert (
        classify_intent("why did you include TCS", artifact_path).intent
        is AssistantIntent.EXPLAIN_STOCK_INCLUSION
    )
    assert (
        classify_intent("what if the market crashes", artifact_path).intent
        is AssistantIntent.HYPOTHETICAL_SHOCK
    )
