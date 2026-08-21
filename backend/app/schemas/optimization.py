from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.optimization.types import SolverName


class OptimizeRequest(BaseModel):
    budget: float = Field(gt=0)
    target_return: float | None = None
    risk_tolerance: float | None = Field(default=None, gt=0)
    max_single_weight: float = Field(default=0.20, gt=0, le=1)
    min_holdings: int | None = Field(default=None, ge=1)
    max_holdings: int | None = Field(default=None, ge=1)
    min_lot_weight: float = Field(default=0.01, ge=0)
    sector_caps: dict[str, float] = Field(default_factory=dict)
    default_sector_cap: float = Field(default=0.35, gt=0, le=1)
    solver: SolverName = SolverName.AUTO
    risk_free_rate: float = 0.0
    lookback_days: int | None = Field(default=None, ge=2)
    label: str = Field(default="Optimized portfolio", max_length=160)
    return_estimation_method: Literal["historical_mean", "ml_forecast"] = (
        "historical_mean"
    )

    @model_validator(mode="after")
    def require_objective_constraint(self) -> OptimizeRequest:
        if self.target_return is None and self.risk_tolerance is None:
            raise ValueError("target_return or risk_tolerance is required")
        if (
            self.min_holdings is not None
            and self.max_holdings is not None
            and self.min_holdings > self.max_holdings
        ):
            raise ValueError("min_holdings cannot exceed max_holdings")
        return self


class OptimizationRunResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    status: str
    solver_used: str
    solve_time_ms: int | None
    message: str | None = None
