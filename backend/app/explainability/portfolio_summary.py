"""Deterministic plain-language portfolio summary generation."""

from __future__ import annotations


def risk_level_bucket(volatility: float) -> str:
    if volatility < 0.12:
        return "lower-risk"
    if volatility < 0.22:
        return "moderate-risk"
    return "higher-risk"


def build_portfolio_summary(
    expected_return: float,
    expected_volatility: float,
    weights: dict[str, float],
    sectors: dict[str, str],
) -> str:
    """Create a stable 2-sentence summary from structured values only."""

    included = {symbol: weight for symbol, weight in weights.items() if weight > 1e-6}
    if not included:
        raise ValueError("summary requires at least one included holding")
    ranked = sorted(included.items(), key=lambda item: (-item[1], item[0]))
    top = ranked[:3]
    top_text = ", ".join(f"{symbol} ({weight:.1%})" for symbol, weight in top)
    sector_count = len({sectors[symbol] for symbol in included})
    return (
        f"The portfolio targets an annualized return of {expected_return:.1%} with "
        f"{expected_volatility:.1%} expected volatility, a {risk_level_bucket(expected_volatility)} "
        f"profile spread across {sector_count} sectors. Its largest positions are {top_text}; "
        "these weights reflect the configured return, risk, concentration, and diversification constraints."
    )
