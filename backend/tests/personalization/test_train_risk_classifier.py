import joblib

from app.personalization.generate_training_data import generate_training_data
from app.personalization.train_risk_classifier import (
    load_training_csv,
    train_risk_classifier,
)


def test_both_models_are_reported_and_selected_model_exceeds_accuracy_floor(tmp_path) -> None:
    data_path = generate_training_data(2_500, 42, tmp_path / "labels.csv")
    artifact_path = tmp_path / "risk.joblib"
    result = train_risk_classifier(data_path, artifact_path)
    artifact = joblib.load(artifact_path)

    assert set(result.candidate_metrics) == {"logistic_regression", "random_forest"}
    assert result.test_accuracy >= 0.85
    assert result.train_accuracy >= 0.85
    assert result.training_rows == 2_000
    assert result.test_rows == 500
    assert artifact["label_source"].startswith("transparent weighted rubric")
    assert artifact["feature_reasoning"]
    features, labels = load_training_csv(data_path)
    assert features.shape == (2_500, 6)
    assert labels.shape == (2_500,)
