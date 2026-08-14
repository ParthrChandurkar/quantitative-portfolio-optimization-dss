from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class WalkForwardRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    rebalance_frequency: Literal["weekly", "monthly", "quarterly", "annually"] = (
        "monthly"
    )
    lookback_days: int = Field(default=252, ge=2, le=2520)

    @model_validator(mode="after")
    def validate_range(self) -> WalkForwardRequest:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date >= self.end_date
        ):
            raise ValueError("start_date must precede end_date")
        return self


class WalkForwardResult(BaseModel):
    id: UUID
    portfolio_id: UUID
    rebalance_frequency: str
    lookback_days: int
    start_date: date
    end_date: date
    constraints_snapshot: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime


WalkForwardRunResponse = WalkForwardResult
