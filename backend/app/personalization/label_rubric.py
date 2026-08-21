"""Human-readable ground-truth rubric for synthetic risk labels.

These labels are policy labels, not observations of real investor outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from app.personalization.questionnaire import FEATURE_NAMES, answers_to_features


class RiskCategory(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


# Loss behavior and time horizon receive the greatest weights because willingness to
# withstand loss and capacity to wait are the most direct risk-tolerance indicators.
RUBRIC_WEIGHTS: dict[str, float] = {
    "age_bracket": 1.0,
    "investment_horizon": 2.0,
    "income_stability": 1.5,
    "loss_reaction": 3.0,
    "experience_level": 1.5,
    "financial_dependents": 1.0,
}
CONSERVATIVE_MAX_SCORE = 21.0
MODERATE_MAX_SCORE = 31.0


def rubric_score(answers: Mapping[str, str]) -> float:
    features = answers_to_features(answers)
    return sum(
        value * RUBRIC_WEIGHTS[name]
        for name, value in zip(FEATURE_NAMES, features, strict=True)
    )


def label_answers(answers: Mapping[str, str]) -> RiskCategory:
    score = rubric_score(answers)
    if score <= CONSERVATIVE_MAX_SCORE:
        return RiskCategory.CONSERVATIVE
    if score <= MODERATE_MAX_SCORE:
        return RiskCategory.MODERATE
    return RiskCategory.AGGRESSIVE
