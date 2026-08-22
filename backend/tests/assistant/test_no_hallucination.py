import re
from dataclasses import asdict
from typing import Any

from app.assistant.answer_templates import (
    TemplateAnswer,
    allocation_rationale,
    diversification_question,
    hypothetical_shock,
    portfolio_risk_summary,
    stock_explanation,
    unknown_fallback,
)

NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _numbers(value: Any) -> list[float]:
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        return [float(match) for match in NUMBER.findall(value)]
    if isinstance(value, dict):
        return [number for item in value.values() for number in _numbers(item)]
    if isinstance(value, (list, tuple)):
        return [number for item in value for number in _numbers(item)]
    return []


def _assert_every_answer_number_is_grounded(answer: TemplateAnswer) -> None:
    answer_numbers = _numbers(answer.answer)
    source_numbers = _numbers([asdict(item) for item in answer.grounding])
    for number in answer_numbers:
        assert any(number == source for source in source_numbers), (
            number,
            answer.answer,
            source_numbers,
        )


def test_every_number_across_all_answer_intents_is_traceable() -> None:
    answers = (
        stock_explanation(
            "TCS", "TCS has contribution 0.123 and rank 2.", included=True
        ),
        stock_explanation("INFY", "INFY was excluded at cap 0.35.", included=False),
        portfolio_risk_summary(
            {
                "realized_annualized_return": 0.103,
                "realized_annualized_volatility": 0.152,
                "max_drawdown": -0.133,
                "realized_sharpe_ratio": 0.678,
            }
        ),
        allocation_rationale("The stored summary reports 6 holdings across 4 sectors."),
        hypothetical_shock(
            "MARKET_CRASH",
            {
                "expected_return_delta": -0.2,
                "volatility_delta": 0.02,
                "sharpe_ratio_delta": -0.98,
                "diversification_score_delta": 0.0,
            },
        ),
        diversification_question(
            {
                "overall_score": 81.5,
                "stock_concentration_hhi": 0.18,
                "sector_concentration_hhi": 0.31,
            }
        ),
        unknown_fallback(),
    )
    for answer in answers:
        _assert_every_answer_number_is_grounded(answer)
