from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.assistant.intents import AssistantIntent


class AssistantQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1_000)


class AssistantGrounding(BaseModel):
    source: str
    fields: list[str]
    values: dict[str, Any]


class AssistantAnswerResponse(BaseModel):
    answer: str
    intent: AssistantIntent
    confidence: float
    grounding: list[AssistantGrounding]
    is_fallback: bool
