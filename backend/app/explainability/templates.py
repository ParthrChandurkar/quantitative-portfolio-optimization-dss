"""Pure, deterministic narrative templates for each reason taxonomy value."""

from __future__ import annotations

from collections.abc import Callable

from app.explainability.reason_taxonomy import PrimaryReason


def high_risk_adjusted_return(symbol: str, mu: float, risk_reduction: float) -> str:
    return (
        f"{symbol} was selected for its {mu:.1%} expected return with an efficient risk "
        f"contribution; its diversification effect changes portfolio risk by {risk_reduction:.2%}."
    )


def diversification_value(symbol: str, mu: float, risk_reduction: float) -> str:
    return (
        f"{symbol} adds diversification value alongside its {mu:.1%} expected return, "
        f"reducing correlated portfolio risk by approximately {abs(risk_reduction):.2%}."
    )


def cardinality_floor(symbol: str, k_min: int) -> str:
    return (
        f"{symbol} is included primarily because the portfolio requires at least {k_min} "
        "holdings; among the additional candidates it caused the smallest objective penalty."
    )


def sector_requirement(symbol: str, sector: str) -> str:
    return (
        f"{symbol} represents {sector} because the configured minimum-sector rule requires "
        "that sector to be present in the portfolio."
    )


def dominated(symbol: str, dominant_symbol: str) -> str:
    return (
        f"{symbol} was excluded because {dominant_symbol} offered at least as much expected "
        "return with an equal or better risk and correlation profile."
    )


def sector_cap_binding(
    symbol: str, sector: str, cap: float, occupying_symbols: tuple[str, ...]
) -> str:
    occupants = ", ".join(occupying_symbols) if occupying_symbols else "existing holdings"
    return (
        f"{symbol} was excluded because {sector} is at its {cap:.0%} cap, currently occupied "
        f"by {occupants}."
    )


def cardinality_excluded(symbol: str, k_max: int) -> str:
    return (
        f"{symbol} was the next eligible candidate but the portfolio is limited to {k_max} "
        "holdings, so it was excluded by the cardinality ceiling."
    )


def single_weight_cap_indirect(symbol: str, w_max: float) -> str:
    return (
        f"{symbol} was excluded because a position large enough to improve the solution would "
        f"have required exceeding the {w_max:.0%} single-stock cap given its correlation profile."
    )


Template = Callable[..., str]
TEMPLATES: dict[PrimaryReason, Template] = {
    PrimaryReason.HIGH_RISK_ADJUSTED_RETURN: high_risk_adjusted_return,
    PrimaryReason.DIVERSIFICATION_VALUE: diversification_value,
    PrimaryReason.CARDINALITY_FLOOR: cardinality_floor,
    PrimaryReason.SECTOR_REQUIREMENT: sector_requirement,
    PrimaryReason.DOMINATED: dominated,
    PrimaryReason.SECTOR_CAP_BINDING: sector_cap_binding,
    PrimaryReason.CARDINALITY_EXCLUDED: cardinality_excluded,
    PrimaryReason.SINGLE_WEIGHT_CAP_INDIRECT: single_weight_cap_indirect,
}

