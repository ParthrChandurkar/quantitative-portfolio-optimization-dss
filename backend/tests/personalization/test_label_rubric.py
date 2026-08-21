from app.personalization.label_rubric import RiskCategory, label_answers, rubric_score


def test_hand_checked_conservative_moderate_and_aggressive_profiles() -> None:
    conservative = {"age_bracket":"60_plus","investment_horizon":"under_3_years","income_stability":"unstable","loss_reaction":"sell_all","experience_level":"none","financial_dependents":"three_or_more"}
    moderate = {"age_bracket":"30_44","investment_horizon":"6_10_years","income_stability":"stable","loss_reaction":"hold","experience_level":"intermediate","financial_dependents":"one_or_two"}
    aggressive = {"age_bracket":"under_30","investment_horizon":"over_10_years","income_stability":"highly_stable","loss_reaction":"buy_more","experience_level":"advanced","financial_dependents":"none"}

    assert label_answers(conservative) is RiskCategory.CONSERVATIVE
    assert label_answers(moderate) is RiskCategory.MODERATE
    assert rubric_score(moderate) == 29.0
    assert label_answers(aggressive) is RiskCategory.AGGRESSIVE
