from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class AnalyticsQuery(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    horizon_years: int = Field(default=10, ge=0, le=50)
    estimation_end_date: date | None = None
