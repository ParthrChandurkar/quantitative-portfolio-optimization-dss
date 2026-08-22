from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    snapshot_id: uuid.UUID | None
    stock_id: uuid.UUID | None
    alert_type: str
    severity: str
    message: str
    grounding: dict[str, Any]
    acknowledged: bool
    created_at: datetime
