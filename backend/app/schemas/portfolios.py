from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PortfolioCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class PortfolioUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    latest_snapshot: dict | None = None


class SnapshotResponse(BaseModel):
    id: uuid.UUID
    label: str
    expected_return: float | None
    expected_volatility: float | None
    sharpe_ratio: float | None
    diversification_score: float | None
    is_baseline: bool
    created_at: datetime
