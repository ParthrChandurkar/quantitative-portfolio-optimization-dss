from __future__ import annotations

import pytest

from app.explainability.portfolio_summary import (
    build_portfolio_summary,
    risk_level_bucket,
)


def test_summary_contains_top_symbols_and_sector_count() -> None:
    summary = build_portfolio_summary(
        0.168,
        0.196,
        {"HDFCBANK": 0.4, "INFY": 0.35, "ITC": 0.25},
        {"HDFCBANK": "Financials", "INFY": "IT", "ITC": "FMCG"},
    )
    assert "HDFCBANK (40.0%)" in summary
    assert "INFY (35.0%)" in summary
    assert "ITC (25.0%)" in summary
    assert "3 sectors" in summary
    assert len(summary.split(". ")) == 2


def test_different_portfolios_never_produce_identical_summaries() -> None:
    first = build_portfolio_summary(0.15, 0.10, {"A": 1.0}, {"A": "Energy"})
    second = build_portfolio_summary(
        0.18, 0.25, {"B": 0.5, "C": 0.5}, {"B": "IT", "C": "FMCG"}
    )
    assert first != second
    assert "lower-risk" in first
    assert "higher-risk" in second
    assert risk_level_bucket(0.15) == "moderate-risk"


def test_empty_portfolio_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_portfolio_summary(0.1, 0.2, {}, {})

