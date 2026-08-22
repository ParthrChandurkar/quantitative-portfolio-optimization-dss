"""Pure alert messages over explicit grounding payloads."""

from __future__ import annotations

from typing import Any


def risk_drift_message(grounding: dict[str, Any]) -> str:
    return (
        f"Portfolio expected volatility is {grounding['expected_volatility']}, above "
        f"the {grounding['profile_category']} profile target of "
        f"{grounding['recommended_risk_tolerance']}."
    )


def diversification_drift_message(grounding: dict[str, Any]) -> str:
    return (
        f"Portfolio diversification score is {grounding['diversification_score']}, "
        f"below the {grounding['profile_category']} profile reference minimum of "
        f"{grounding['reference_minimum']}."
    )


def stock_anomaly_message(grounding: dict[str, Any]) -> str:
    return (
        f"{grounding['symbol']} has anomaly score {grounding['anomaly_score']}, "
        "indicating unusual behavior relative to its own historical feature distribution."
    )
