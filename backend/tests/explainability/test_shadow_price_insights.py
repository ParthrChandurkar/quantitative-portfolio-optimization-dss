from __future__ import annotations

from app.explainability.shadow_price_insights import build_shadow_price_insights
from app.optimization.types import ConstraintReport


def test_immaterial_or_nonbinding_constraint_produces_no_insight() -> None:
    reports = (
        ConstraintReport("C4 Sector cap: Financials", True, True, 0.0, 0.00001),
        ConstraintReport("C3 Max single-stock weight", True, False, 0.1, 2.0),
    )
    assert build_shadow_price_insights(reports, materiality_threshold=0.001) == ()


def test_numeric_claim_equals_shadow_price_times_delta_exactly() -> None:
    report = ConstraintReport("C4 Sector cap: Financials", True, True, 0.0, 0.8)
    insight = build_shadow_price_insights((report,), relaxation_delta=0.05)[0]
    assert insight.projected_objective_change == 0.8 * 0.05
    assert "0.040000" in insight.narrative
    assert "Financials sector cap by 5%" in insight.narrative


def test_external_shadow_price_lookup_and_generic_action() -> None:
    report = ConstraintReport("C6 Cardinality", True, True, 0.0)
    insight = build_shadow_price_insights((report,), {"C6 Cardinality": -0.2})[0]
    assert insight.shadow_price == -0.2
    assert "relaxing C6 Cardinality" in insight.narrative


def test_solver_constraint_names_map_to_display_reports() -> None:
    report = ConstraintReport("C4 Sector cap: IT", True, True, 0.0)
    insight = build_shadow_price_insights((report,), {"C4_SectorCap_IT": -0.4})[0]
    assert insight.shadow_price == -0.4
    assert "IT sector cap" in insight.narrative
