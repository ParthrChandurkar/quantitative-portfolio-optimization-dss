from app.assistant.slot_extraction import (
    extract_shock,
    extract_slots,
    extract_stock_symbol,
)
from app.scenarios.types import ScenarioType

UNIVERSE = ("RELIANCE", "TCS", "HDFCBANK", "M&M")


def test_symbol_extraction_supports_exact_and_conservative_fuzzy_matches() -> None:
    assert extract_stock_symbol("Why is TCS included?", UNIVERSE) == "TCS"
    assert extract_stock_symbol("Explain HDFCBNK", UNIVERSE) == "HDFCBANK"
    assert extract_stock_symbol("How risky is this?", UNIVERSE) is None


def test_shock_type_and_magnitude_extraction() -> None:
    kind, params = extract_shock("What if the market crashes 20%?")
    assert kind is ScenarioType.MARKET_CRASH
    assert params == {"delta": -0.20, "kappa_vol": 0.5}
    kind, params = extract_shock("What if interest rates rise 1%?")
    assert kind is ScenarioType.RATE_INCREASE
    assert params == {"delta_r": 0.01}
    slots = extract_slots(
        "What if the IT sector drops 30%?",
        UNIVERSE,
        ("IT", "Energy"),
        include_shock=True,
    )
    assert slots.scenario_type is ScenarioType.SECTOR_CRASH
    assert slots.scenario_params == {"sector": "IT", "delta_s": -0.30}
