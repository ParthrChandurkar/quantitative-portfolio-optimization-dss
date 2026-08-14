from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.reports.service import ReportType


class ReportCreateRequest(BaseModel):
    report_type: ReportType


class ReportResponse(BaseModel):
    id: uuid.UUID
    snapshot_id: uuid.UUID
    report_type: str
    file_path: str
    generated_at: datetime
    download_url: str
