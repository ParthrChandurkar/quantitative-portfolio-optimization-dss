"""Deterministic symbol and scenario-parameter extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import get_close_matches

from app.scenarios.types import ScenarioType

PERCENT_PATTERN = re.compile(r"(?<!\w)(\d+(?:\.\d+)?)\s*%")


@dataclass(frozen=True, slots=True)
class AssistantSlots:
    stock_symbol: str | None = None
    scenario_type: ScenarioType | None = None
    scenario_params: dict[str, object] = field(default_factory=dict)


def extract_stock_symbol(question: str, universe: tuple[str, ...]) -> str | None:
    upper = question.upper()
    for symbol in sorted(universe, key=len, reverse=True):
        if re.search(rf"(?<![A-Z0-9]){re.escape(symbol.upper())}(?![A-Z0-9])", upper):
            return symbol
    tokens = re.findall(r"[A-Z0-9&-]{2,}", upper)
    normalized = {symbol.upper(): symbol for symbol in universe}
    for token in tokens:
        match = get_close_matches(token, normalized, n=1, cutoff=0.84)
        if match:
            return normalized[match[0]]
    return None


def _magnitude(question: str) -> float | None:
    match = PERCENT_PATTERN.search(question)
    return float(match.group(1)) / 100 if match else None


def extract_shock(
    question: str, sectors: tuple[str, ...] = ()
) -> tuple[ScenarioType, dict[str, object]]:
    lowered = question.casefold()
    magnitude = _magnitude(question)
    if "interest" in lowered or "rate" in lowered:
        delta = (
            magnitude if magnitude is not None and 0.0025 <= magnitude <= 0.03 else 0.01
        )
        return ScenarioType.RATE_INCREASE, {"delta_r": delta}
    if "inflation" in lowered:
        delta = (
            magnitude if magnitude is not None and 0.005 <= magnitude <= 0.05 else 0.02
        )
        return ScenarioType.INFLATION, {"delta_pi": delta}
    for sector in sectors:
        if sector.casefold() in lowered and any(
            word in lowered for word in ("crash", "fall", "drop", "decline")
        ):
            delta = -(
                magnitude
                if magnitude is not None and 0.10 <= magnitude <= 0.60
                else 0.20
            )
            return ScenarioType.SECTOR_CRASH, {"sector": sector, "delta_s": delta}
    delta = -(
        magnitude if magnitude is not None and 0.05 <= magnitude <= 0.50 else 0.20
    )
    return ScenarioType.MARKET_CRASH, {"delta": delta, "kappa_vol": 0.5}


def extract_slots(
    question: str,
    universe: tuple[str, ...],
    sectors: tuple[str, ...] = (),
    *,
    include_shock: bool = False,
) -> AssistantSlots:
    symbol = extract_stock_symbol(question, universe)
    if not include_shock:
        return AssistantSlots(stock_symbol=symbol)
    scenario_type, params = extract_shock(question, sectors)
    return AssistantSlots(symbol, scenario_type, params)
