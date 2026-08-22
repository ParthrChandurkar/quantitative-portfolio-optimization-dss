"""Pure deterministic answer templates over explicit structured source bundles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GroundingItem:
    source: str
    fields: tuple[str, ...]
    values: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TemplateAnswer:
    answer: str
    grounding: tuple[GroundingItem, ...]
    is_fallback: bool = False


def stock_explanation(
    symbol: str, narrative_text: str, *, included: bool
) -> TemplateAnswer:
    decision = "inclusion" if included else "exclusion"
    return TemplateAnswer(
        narrative_text,
        (
            GroundingItem(
                "explanation_items",
                ("symbol", "decision", "narrative_text"),
                {
                    "symbol": symbol,
                    "decision": decision,
                    "narrative_text": narrative_text,
                },
            ),
        ),
    )


def portfolio_risk_summary(
    risk_metrics: dict[str, float], portfolio_summary: str | None = None
) -> TemplateAnswer:
    fields = (
        "realized_annualized_return",
        "realized_annualized_volatility",
        "max_drawdown",
        "realized_sharpe_ratio",
    )
    values = {field: float(risk_metrics[field]) for field in fields}
    answer = (
        f"The out-of-sample realized annualized return is {values['realized_annualized_return']}; "
        f"realized annualized volatility is {values['realized_annualized_volatility']}; "
        f"maximum drawdown is {values['max_drawdown']}; and realized Sharpe ratio is "
        f"{values['realized_sharpe_ratio']}."
    )
    grounding = [GroundingItem("analytics.risk_metrics", fields, values)]
    if portfolio_summary is not None:
        answer = f"{answer} {portfolio_summary}"
        grounding.append(
            GroundingItem(
                "explainability.portfolio_summary",
                ("summary",),
                {"summary": portfolio_summary},
            )
        )
    return TemplateAnswer(answer, tuple(grounding))


def allocation_rationale(summary: str) -> TemplateAnswer:
    return TemplateAnswer(
        summary,
        (
            GroundingItem(
                "explainability.portfolio_summary", ("summary",), {"summary": summary}
            ),
        ),
    )


def hypothetical_shock(
    scenario_type: str, comparison: dict[str, Any]
) -> TemplateAnswer:
    fields = (
        "expected_return_delta",
        "volatility_delta",
        "sharpe_ratio_delta",
        "diversification_score_delta",
    )
    values = {field: float(comparison[field]) for field in fields}
    answer = (
        f"The real {scenario_type} re-solve produced expected-return delta "
        f"{values['expected_return_delta']}, volatility delta {values['volatility_delta']}, "
        f"Sharpe-ratio delta {values['sharpe_ratio_delta']}, and diversification-score "
        f"delta {values['diversification_score_delta']}."
    )
    return TemplateAnswer(
        answer,
        (GroundingItem("scenario_runs.comparison", fields, values),),
    )


def diversification_question(breakdown: dict[str, float]) -> TemplateAnswer:
    fields = ("overall_score", "stock_concentration_hhi", "sector_concentration_hhi")
    values = {field: float(breakdown[field]) for field in fields}
    answer = (
        f"The diversification score is {values['overall_score']}; stock-concentration HHI "
        f"is {values['stock_concentration_hhi']}; and sector-concentration HHI is "
        f"{values['sector_concentration_hhi']}."
    )
    return TemplateAnswer(
        answer,
        (GroundingItem("explainability.diversification", fields, values),),
    )


def unknown_fallback() -> TemplateAnswer:
    return TemplateAnswer(
        "I could not confidently match that question to stored portfolio data. Try asking why a stock is included or excluded, how risky or diversified the portfolio is, why it has these allocations, or what happens in a market crash.",
        (),
        True,
    )
