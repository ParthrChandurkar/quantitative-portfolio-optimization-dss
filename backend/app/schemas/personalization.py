from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.personalization.label_rubric import RiskCategory
from app.personalization.questionnaire import (
    AgeBracket,
    Dependents,
    ExperienceLevel,
    IncomeStability,
    InvestmentHorizon,
    LossReaction,
)


class QuestionnaireAnswers(BaseModel):
    age_bracket: AgeBracket
    investment_horizon: InvestmentHorizon
    income_stability: IncomeStability
    loss_reaction: LossReaction
    experience_level: ExperienceLevel
    financial_dependents: Dependents


class RiskProfileRequest(BaseModel):
    answers: QuestionnaireAnswers


class RecommendedConstraints(BaseModel):
    risk_tolerance: float
    max_single_weight: float
    default_sector_cap: float


class RiskProfileResponse(BaseModel):
    id: uuid.UUID
    predicted_category: RiskCategory
    category_confidence: float
    probabilities: dict[str, float]
    recommended_constraints: RecommendedConstraints
    questionnaire_answers: QuestionnaireAnswers
    model_name: str
    created_at: datetime
