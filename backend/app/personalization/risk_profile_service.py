"""Risk-category inference and separately auditable optimization defaults."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.db.models import User, UserRiskProfile
from app.personalization.label_rubric import RiskCategory
from app.personalization.questionnaire import FEATURE_NAMES, answers_to_features
from app.personalization.train_risk_classifier import DEFAULT_ARTIFACT_PATH

# The classifier selects only a category. Product policy maps that category to
# editable OR inputs here, so changing a constraint never requires retraining ML.
RECOMMENDED_CONSTRAINTS: dict[RiskCategory, dict[str, float]] = {
    RiskCategory.CONSERVATIVE: {
        "risk_tolerance": 0.15,
        "max_single_weight": 0.10,
        "default_sector_cap": 0.25,
    },
    RiskCategory.MODERATE: {
        "risk_tolerance": 0.22,
        "max_single_weight": 0.15,
        "default_sector_cap": 0.30,
    },
    RiskCategory.AGGRESSIVE: {
        "risk_tolerance": 0.35,
        "max_single_weight": 0.20,
        "default_sector_cap": 0.35,
    },
}


@dataclass(frozen=True, slots=True)
class RiskProfileResult:
    predicted_category: RiskCategory
    category_confidence: float
    probabilities: dict[str, float]
    recommended_constraints: dict[str, float]
    model_name: str


def predict_risk_profile(
    answers: Mapping[str, str], artifact_path: Path = DEFAULT_ARTIFACT_PATH
) -> RiskProfileResult:
    artifact = joblib.load(artifact_path)
    if tuple(artifact["feature_names"]) != FEATURE_NAMES:
        raise ValueError("risk-classifier artifact feature schema is incompatible")
    model = artifact["model"]
    matrix = np.asarray([answers_to_features(answers)], dtype=float)
    probabilities_array = model.predict_proba(matrix)[0]
    probabilities = {
        str(category): float(probability)
        for category, probability in zip(
            model.classes_, probabilities_array, strict=True
        )
    }
    predicted = RiskCategory(str(model.predict(matrix)[0]))
    return RiskProfileResult(
        predicted,
        probabilities[predicted.value],
        probabilities,
        dict(RECOMMENDED_CONSTRAINTS[predicted]),
        str(artifact["selected_model"]),
    )


def stored_profile_payload(
    stored: UserRiskProfile,
    *,
    probabilities: dict[str, float] | None = None,
    model_name: str = "stored_prediction",
) -> dict[str, object]:
    return {
        "id": stored.id,
        "predicted_category": stored.predicted_category,
        "category_confidence": float(stored.category_confidence),
        "probabilities": probabilities or {
            stored.predicted_category: float(stored.category_confidence)
        },
        "recommended_constraints": stored.recommended_constraints,
        "questionnaire_answers": stored.questionnaire_answers,
        "model_name": model_name,
        "created_at": stored.created_at,
    }


async def predict_and_store_risk_profile(
    session: AsyncSession,
    user: User,
    answers: Mapping[str, str],
) -> dict[str, object]:
    result = predict_risk_profile(answers)
    stored = UserRiskProfile(
        user_id=user.id,
        questionnaire_answers=dict(answers),
        predicted_category=result.predicted_category.value,
        category_confidence=Decimal(str(result.category_confidence)),
        recommended_constraints=result.recommended_constraints,
    )
    user.risk_profile_default = result.predicted_category.value
    session.add(stored)
    await session.commit()
    await session.refresh(stored)
    return stored_profile_payload(
        stored,
        probabilities=result.probabilities,
        model_name=result.model_name,
    )


async def get_latest_risk_profile(
    session: AsyncSession, user: User
) -> dict[str, object]:
    stored = await session.scalar(
        select(UserRiskProfile)
        .where(UserRiskProfile.user_id == user.id)
        .order_by(UserRiskProfile.created_at.desc(), UserRiskProfile.id.desc())
        .limit(1)
    )
    if stored is None:
        raise APIError(404, "RISK_PROFILE_NOT_FOUND", "Complete the risk questionnaire first")
    prediction = predict_risk_profile(stored.questionnaire_answers)
    return stored_profile_payload(
        stored,
        probabilities=prediction.probabilities,
        model_name=prediction.model_name,
    )
