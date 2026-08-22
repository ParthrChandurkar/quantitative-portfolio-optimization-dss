from app.assistant.answer_templates import (
    allocation_rationale,
    diversification_question,
    hypothetical_shock,
    portfolio_risk_summary,
    stock_explanation,
    unknown_fallback,
)


def test_templates_use_only_supplied_structured_values() -> None:
    stock = stock_explanation(
        "TCS", "TCS contributes 0.12 to expected return.", included=True
    )
    assert stock.answer == "TCS contributes 0.12 to expected return."
    risk = portfolio_risk_summary(
        {
            "realized_annualized_return": 0.1,
            "realized_annualized_volatility": 0.2,
            "max_drawdown": -0.08,
            "realized_sharpe_ratio": 0.5,
        }
    )
    assert "0.2" in risk.answer and "-0.08" in risk.answer
    allocation = allocation_rationale("Stored summary with 3 sectors.")
    assert allocation.answer == "Stored summary with 3 sectors."
    shock = hypothetical_shock(
        "MARKET_CRASH",
        {
            "expected_return_delta": -0.2,
            "volatility_delta": 0.03,
            "sharpe_ratio_delta": -0.7,
            "diversification_score_delta": 1.2,
        },
    )
    assert "-0.2" in shock.answer
    diversified = diversification_question(
        {
            "overall_score": 82.0,
            "stock_concentration_hhi": 0.2,
            "sector_concentration_hhi": 0.3,
        }
    )
    assert "82.0" in diversified.answer
    assert unknown_fallback().is_fallback is True
    assert unknown_fallback().grounding == ()
