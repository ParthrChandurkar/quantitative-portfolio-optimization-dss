"""Fixed, auditable onboarding questions and numeric feature encoding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class AgeBracket(StrEnum):
    UNDER_30 = "under_30"
    AGE_30_44 = "30_44"
    AGE_45_59 = "45_59"
    AGE_60_PLUS = "60_plus"


class InvestmentHorizon(StrEnum):
    UNDER_3_YEARS = "under_3_years"
    YEARS_3_5 = "3_5_years"
    YEARS_6_10 = "6_10_years"
    OVER_10_YEARS = "over_10_years"


class IncomeStability(StrEnum):
    UNSTABLE = "unstable"
    VARIABLE = "variable"
    STABLE = "stable"
    HIGHLY_STABLE = "highly_stable"


class LossReaction(StrEnum):
    SELL_ALL = "sell_all"
    SELL_SOME = "sell_some"
    HOLD = "hold"
    BUY_MORE = "buy_more"


class ExperienceLevel(StrEnum):
    NONE = "none"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Dependents(StrEnum):
    THREE_OR_MORE = "three_or_more"
    ONE_OR_TWO = "one_or_two"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class QuestionDefinition:
    key: str
    prompt: str
    options: tuple[tuple[str, str], ...]


QUESTIONNAIRE: tuple[QuestionDefinition, ...] = (
    QuestionDefinition("age_bracket", "What is your age bracket?", (("under_30", "Under 30"), ("30_44", "30–44"), ("45_59", "45–59"), ("60_plus", "60 or above"))),
    QuestionDefinition("investment_horizon", "How long can this money remain invested?", (("under_3_years", "Under 3 years"), ("3_5_years", "3–5 years"), ("6_10_years", "6–10 years"), ("over_10_years", "More than 10 years"))),
    QuestionDefinition("income_stability", "How stable is your income?", (("unstable", "Unstable"), ("variable", "Variable"), ("stable", "Stable"), ("highly_stable", "Highly stable"))),
    QuestionDefinition("loss_reaction", "How would you react to a temporary 20% portfolio loss?", (("sell_all", "Sell all"), ("sell_some", "Sell some"), ("hold", "Hold"), ("buy_more", "Invest more"))),
    QuestionDefinition("experience_level", "What is your investment experience?", (("none", "None"), ("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced"))),
    QuestionDefinition("financial_dependents", "How many people financially depend on you?", (("three_or_more", "Three or more"), ("one_or_two", "One or two"), ("none", "None"))),
)

FEATURE_NAMES: tuple[str, ...] = tuple(question.key for question in QUESTIONNAIRE)

FEATURE_POINTS: dict[str, dict[str, int]] = {
    "age_bracket": {"under_30": 4, "30_44": 3, "45_59": 2, "60_plus": 1},
    "investment_horizon": {"under_3_years": 1, "3_5_years": 2, "6_10_years": 3, "over_10_years": 4},
    "income_stability": {"unstable": 1, "variable": 2, "stable": 3, "highly_stable": 4},
    "loss_reaction": {"sell_all": 1, "sell_some": 2, "hold": 3, "buy_more": 4},
    "experience_level": {"none": 1, "beginner": 2, "intermediate": 3, "advanced": 4},
    "financial_dependents": {"three_or_more": 1, "one_or_two": 2, "none": 4},
}


def answers_to_features(answers: Mapping[str, str]) -> tuple[float, ...]:
    """Encode answers in the stable feature order used by training and inference."""

    if set(answers) != set(FEATURE_NAMES):
        raise ValueError(f"answers must contain exactly: {', '.join(FEATURE_NAMES)}")
    try:
        return tuple(float(FEATURE_POINTS[name][str(answers[name])]) for name in FEATURE_NAMES)
    except KeyError as error:
        raise ValueError(f"invalid questionnaire option: {error.args[0]}") from None
