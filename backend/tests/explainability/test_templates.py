from __future__ import annotations

from app.explainability.reason_taxonomy import PrimaryReason
from app.explainability.templates import (
    TEMPLATES,
    cardinality_excluded,
    cardinality_floor,
    diversification_value,
    dominated,
    high_risk_adjusted_return,
    sector_cap_binding,
    sector_requirement,
    single_weight_cap_indirect,
)


def test_all_taxonomy_values_have_a_template() -> None:
    assert set(TEMPLATES) == set(PrimaryReason)


def test_templates_are_parameterized_and_deterministic() -> None:
    calls = [
        lambda: high_risk_adjusted_return("INFY", 0.17, -0.02),
        lambda: diversification_value("ITC", 0.11, -0.03),
        lambda: cardinality_floor("LT", 8),
        lambda: sector_requirement("SUNPHARMA", "Healthcare"),
        lambda: dominated("WIPRO", "TCS"),
        lambda: sector_cap_binding("INFY", "IT", 0.4, ("TCS",)),
        lambda: cardinality_excluded("ONGC", 10),
        lambda: single_weight_cap_indirect("RELIANCE", 0.2),
    ]
    first = [call() for call in calls]
    second = [call() for call in calls]
    assert first == second
    assert all(text.endswith(".") for text in first)
    assert "INFY" in first[0] and "17.0%" in first[0]
    assert "TCS" in first[5] and "40%" in first[5]

