from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.assistant.service import answer_latest_question
from app.core.deps import AppSettings, CurrentUser, DBSession
from app.schemas.assistant import AssistantQuestionRequest
from app.schemas.common import success

router = APIRouter(tags=["assistant"])


@router.post("/portfolios/{portfolio_id}/assistant/ask")
async def ask_portfolio_assistant(
    portfolio_id: uuid.UUID,
    request: AssistantQuestionRequest,
    session: DBSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    answer = await answer_latest_question(
        session, user, settings, portfolio_id, request.question
    )
    return success(answer.payload())
