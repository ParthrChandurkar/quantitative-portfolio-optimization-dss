import csv

import pytest

from app.personalization.generate_training_data import (
    generate_training_data,
    generate_training_records,
    write_training_csv,
)


def test_generation_is_deterministic_diverse_and_writes_expected_schema(tmp_path) -> None:
    first = generate_training_records(500, seed=11)
    second = generate_training_records(500, seed=11)
    assert first == second
    assert {row["label"] for row in first} == {"conservative", "moderate", "aggressive"}
    path = generate_training_data(500, 11, tmp_path / "labels.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 500
    assert set(rows[0]) == {
        "age_bracket", "investment_horizon", "income_stability",
        "loss_reaction", "experience_level", "financial_dependents", "label",
    }


def test_generation_rejects_empty_inputs(tmp_path) -> None:
    with pytest.raises(ValueError, match="positive"):
        generate_training_records(0)
    with pytest.raises(ValueError, match="must not be empty"):
        write_training_csv([], tmp_path / "empty.csv")
