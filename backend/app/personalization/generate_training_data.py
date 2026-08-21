"""Generate deterministic synthetic questionnaire responses and rubric labels."""

from __future__ import annotations

import csv
import random
from pathlib import Path

from app.personalization.label_rubric import label_answers
from app.personalization.questionnaire import FEATURE_NAMES

DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "synthetic_risk_labels.csv"


def _choice(randomizer: random.Random, values: tuple[str, ...], weights: tuple[int, ...]) -> str:
    return randomizer.choices(values, weights=weights, k=1)[0]


def generate_training_records(row_count: int = 5_000, seed: int = 42) -> list[dict[str, str]]:
    """Sample plausible combinations, then label them with the explicit rubric.

    Age is sampled around working-age users. Horizon and experience are conditioned on
    age, dependents are most common in middle age, and loss reaction is conditioned on
    experience. These are transparent simulation assumptions—not observed user data.
    """

    if row_count < 1:
        raise ValueError("row_count must be positive")
    rng = random.Random(seed)
    records: list[dict[str, str]] = []
    for _ in range(row_count):
        age = _choice(rng, ("under_30", "30_44", "45_59", "60_plus"), (24, 38, 27, 11))
        if age in {"under_30", "30_44"}:
            horizon_weights = (12, 23, 34, 31)
            experience_weights = (13, 34, 36, 17)
        else:
            horizon_weights = (28, 34, 26, 12)
            experience_weights = (10, 28, 39, 23)
        horizon = _choice(rng, ("under_3_years", "3_5_years", "6_10_years", "over_10_years"), horizon_weights)
        experience = _choice(rng, ("none", "beginner", "intermediate", "advanced"), experience_weights)
        income = _choice(rng, ("unstable", "variable", "stable", "highly_stable"), (10, 25, 45, 20))
        dependents = _choice(
            rng,
            ("three_or_more", "one_or_two", "none"),
            (18, 48, 34) if age in {"30_44", "45_59"} else (8, 27, 65),
        )
        reaction_weights = {
            "none": (40, 35, 20, 5),
            "beginner": (22, 34, 36, 8),
            "intermediate": (9, 23, 50, 18),
            "advanced": (4, 12, 46, 38),
        }[experience]
        reaction = _choice(rng, ("sell_all", "sell_some", "hold", "buy_more"), reaction_weights)
        answers = {
            "age_bracket": age,
            "investment_horizon": horizon,
            "income_stability": income,
            "loss_reaction": reaction,
            "experience_level": experience,
            "financial_dependents": dependents,
        }
        records.append({**answers, "label": label_answers(answers).value})
    return records


def write_training_csv(records: list[dict[str, str]], path: Path = DEFAULT_DATA_PATH) -> Path:
    if not records:
        raise ValueError("records must not be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*FEATURE_NAMES, "label"])
        writer.writeheader()
        writer.writerows(records)
    return path


def generate_training_data(row_count: int = 5_000, seed: int = 42, path: Path = DEFAULT_DATA_PATH) -> Path:
    return write_training_csv(generate_training_records(row_count, seed), path)


if __name__ == "__main__":
    print(generate_training_data())
