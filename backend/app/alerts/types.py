from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AlertType(StrEnum):
    RISK_DRIFT = "RISK_DRIFT"
    DIVERSIFICATION_DRIFT = "DIVERSIFICATION_DRIFT"
    STOCK_ANOMALY = "STOCK_ANOMALY"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Alert:
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    grounding: dict[str, Any]
    snapshot_id: uuid.UUID | None = None
    stock_id: uuid.UUID | None = None
