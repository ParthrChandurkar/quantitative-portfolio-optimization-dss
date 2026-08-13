"""Stable request and result contracts for scenario simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.explainability.service import ExplainabilityBundle
from app.optimization.types import OptimizationInput, OptimizationResult


class ScenarioType(StrEnum):
    MARKET_CRASH = "MARKET_CRASH"
    RATE_INCREASE = "RATE_INCREASE"
    INFLATION = "INFLATION"
    SECTOR_CRASH = "SECTOR_CRASH"
    BUDGET_INCREASE = "BUDGET_INCREASE"
    BUDGET_REDUCTION = "BUDGET_REDUCTION"
    RISK_PROFILE_CHANGE = "RISK_PROFILE_CHANGE"


@dataclass(frozen=True, slots=True)
class ScenarioRequest:
    scenario_type: ScenarioType
    params: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PortfolioMetrics:
    expected_return: float
    volatility: float
    sharpe_ratio: float
    diversification_score: float


@dataclass(frozen=True, slots=True)
class HoldingDelta:
    symbol: str
    base_weight: float
    simulated_weight: float
    delta_w: float
    direction: str


@dataclass(frozen=True, slots=True)
class ScenarioComparison:
    holdings: tuple[HoldingDelta, ...]
    base_metrics: PortfolioMetrics
    simulated_metrics: PortfolioMetrics
    expected_return_delta: float
    volatility_delta: float
    sharpe_ratio_delta: float
    diversification_score_delta: float


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario_type: ScenarioType
    params: dict[str, Any]
    transformed_inputs: OptimizationInput
    base_result: OptimizationResult
    simulated_result: OptimizationResult
    comparison: ScenarioComparison | None
    explanations: ExplainabilityBundle | None
    nominal_expected_return: float | None
    inflation_adjusted_expected_return: float | None
    weights_unchanged: bool
    pure_scale_change: bool
    lot_feasibility_changed: bool
    scale_change_explanation: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

