import pytest

from app.personalization.label_rubric import RiskCategory
from app.personalization.risk_profile_service import (
    RECOMMENDED_CONSTRAINTS,
    predict_risk_profile,
)


@pytest.mark.parametrize(
    ("answers", "category"),
    [
        ({"age_bracket":"60_plus","investment_horizon":"under_3_years","income_stability":"unstable","loss_reaction":"sell_all","experience_level":"none","financial_dependents":"three_or_more"}, RiskCategory.CONSERVATIVE),
        ({"age_bracket":"30_44","investment_horizon":"6_10_years","income_stability":"stable","loss_reaction":"hold","experience_level":"intermediate","financial_dependents":"one_or_two"}, RiskCategory.MODERATE),
        ({"age_bracket":"under_30","investment_horizon":"over_10_years","income_stability":"highly_stable","loss_reaction":"buy_more","experience_level":"advanced","financial_dependents":"none"}, RiskCategory.AGGRESSIVE),
    ],
)
def test_prediction_returns_exact_auditable_constraints(answers, category) -> None:
    result = predict_risk_profile(answers)
    assert result.predicted_category is category
    assert result.recommended_constraints == RECOMMENDED_CONSTRAINTS[category]
    assert sum(result.probabilities.values()) == pytest.approx(1.0)
    assert result.category_confidence == result.probabilities[category.value]
