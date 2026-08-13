"""Stable input and output contracts for the optimization engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


class SolverName(StrEnum):
    AUTO = "Auto"
    SCIPY = "SciPy"
    PULP = "PuLP"
    ORTOOLS = "OR-Tools"


class OptimizationStatus(StrEnum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIME_LIMIT = "TIME_LIMIT"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class OptimizationInput:
    """Complete solver-independent portfolio problem definition.

    Return and risk values use decimal form: 14% is ``0.14``. ``budget`` is INR.
    ``risk_tolerance`` is an annualized volatility ceiling, also in decimal form.
    """

    symbols: tuple[str, ...]
    expected_returns: FloatArray
    covariance: FloatArray
    sectors: tuple[str, ...]
    budget: float
    target_return: float | None = None
    risk_tolerance: float | None = None
    max_single_weight: float = 0.20
    sector_caps: dict[str, float] = field(default_factory=dict)
    default_sector_cap: float = 0.35
    min_holdings: int | None = None
    max_holdings: int | None = None
    min_lot_weight: float = 0.01
    historical_returns: FloatArray | None = None
    solver: SolverName = SolverName.AUTO
    risk_free_rate: float = 0.0
    time_limit_seconds: float = 10.0

    def __post_init__(self) -> None:
        n_assets = len(self.symbols)
        if n_assets == 0:
            raise ValueError("symbols must not be empty")
        if len(set(self.symbols)) != n_assets:
            raise ValueError("symbols must be unique")
        if len(self.sectors) != n_assets:
            raise ValueError("sectors must align with symbols")
        if np.asarray(self.expected_returns).shape != (n_assets,):
            raise ValueError("expected_returns must have shape (n_assets,)")
        if np.asarray(self.covariance).shape != (n_assets, n_assets):
            raise ValueError("covariance must have shape (n_assets, n_assets)")
        if self.historical_returns is not None:
            history = np.asarray(self.historical_returns)
            if history.ndim != 2 or history.shape[1] != n_assets:
                raise ValueError("historical_returns must have shape (observations, n_assets)")
        if self.budget <= 0:
            raise ValueError("budget in INR must be positive")
        if not 0 < self.max_single_weight <= 1:
            raise ValueError("max_single_weight must be in (0, 1]")
        if not 0 <= self.min_lot_weight <= self.max_single_weight:
            raise ValueError("min_lot_weight must be between 0 and max_single_weight")
        if self.target_return is None and self.risk_tolerance is None:
            raise ValueError("target_return or risk_tolerance is required")
        if self.risk_tolerance is not None and self.risk_tolerance <= 0:
            raise ValueError("risk_tolerance must be positive")
        if self.min_holdings is not None and self.min_holdings < 1:
            raise ValueError("min_holdings must be positive when set")
        if self.max_holdings is not None and self.max_holdings < 1:
            raise ValueError("max_holdings must be positive when set")
        if (
            self.min_holdings is not None
            and self.max_holdings is not None
            and self.min_holdings > self.max_holdings
        ):
            raise ValueError("min_holdings cannot exceed max_holdings")

    @property
    def asset_count(self) -> int:
        return len(self.symbols)

    def sector_cap(self, sector: str) -> float:
        return self.sector_caps.get(sector, self.default_sector_cap)


@dataclass(frozen=True, slots=True)
class ConstraintReport:
    """A constraint result shaped for the Phase 2 ``constraint_log`` table."""

    constraint_name: str
    is_satisfied: bool
    is_binding: bool
    slack_value: float | None
    shadow_price: float | None = None
    details: str | None = None


@dataclass(frozen=True, slots=True)
class ExplanationHooks:
    """Numerical evidence shaped for later ``explanation_items`` generation."""

    marginal_return_contributions: dict[str, float]
    marginal_risk_contributions: dict[str, float]
    normalized_risk_shares: dict[str, float]
    excluded_stock_diagnostics: dict[str, str]
    shadow_prices: dict[str, float]


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Framework-independent result returned by :func:`engine.solve`."""

    status: OptimizationStatus
    solver_used: SolverName
    weights: dict[str, float]
    objective_value: float | None
    expected_return: float | None
    expected_variance: float | None
    expected_volatility: float | None
    solve_time_ms: int
    constraint_reports: tuple[ConstraintReport, ...] = ()
    explanation_hooks: ExplanationHooks | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_feasible(self) -> bool:
        return self.status in {OptimizationStatus.OPTIMAL, OptimizationStatus.FEASIBLE}

    def weight_vector(self, symbols: tuple[str, ...]) -> FloatArray:
        return np.asarray([self.weights.get(symbol, 0.0) for symbol in symbols], dtype=float)

