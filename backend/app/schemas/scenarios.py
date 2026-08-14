from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel

from app.scenarios.types import ScenarioType


class ScenarioRunRequest(BaseModel):
    base_snapshot_id: uuid.UUID
    scenario_type: ScenarioType
    params: dict[str, Any]
