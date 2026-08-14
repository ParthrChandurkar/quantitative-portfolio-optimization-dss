from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class StockResponse(BaseModel):
    id: uuid.UUID
    symbol: str
    company_name: str
    sector: str
    industry: str | None
    listed_since: date | None


class SectorResponse(BaseModel):
    id: uuid.UUID
    name: str
