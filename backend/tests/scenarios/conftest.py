from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.optimization.types import OptimizationInput


@pytest.fixture
def golden_problem() -> OptimizationInput:
    path = Path(__file__).parents[1] / "optimization" / "fixtures" / "five_stock_universe.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    volatility = np.asarray(payload["annualized_volatility"], dtype=float)
    return OptimizationInput(
        symbols=tuple(payload["symbols"]),
        expected_returns=np.asarray(payload["expected_returns"], dtype=float),
        covariance=np.diag(volatility**2),
        sectors=tuple(payload["sectors"]),
        budget=payload["budget_inr"],
        target_return=payload["target_return"],
        max_single_weight=payload["max_single_weight"],
        sector_caps=payload["sector_caps"],
        default_sector_cap=payload["default_sector_cap"],
        min_holdings=payload["min_holdings"],
        max_holdings=payload["max_holdings"],
        min_lot_weight=payload["min_lot_weight"],
    )


@pytest.fixture
def base_constraints(golden_problem) -> dict:
    return {
        "sectors": golden_problem.sectors,
        "budget": golden_problem.budget,
        "target_return": golden_problem.target_return,
        "risk_tolerance": golden_problem.risk_tolerance,
        "max_single_weight": golden_problem.max_single_weight,
        "sector_caps": golden_problem.sector_caps,
        "default_sector_cap": golden_problem.default_sector_cap,
        "min_holdings": golden_problem.min_holdings,
        "max_holdings": golden_problem.max_holdings,
        "min_lot_weight": golden_problem.min_lot_weight,
    }

