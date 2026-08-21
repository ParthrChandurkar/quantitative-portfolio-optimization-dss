from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DBSession
from app.personalization import risk_profile_service
from app.schemas.common import success
from app.schemas.personalization import RiskProfileRequest

router = APIRouter(prefix="/me/risk-profile", tags=["personalization"])


@router.post("")
async def create_risk_profile(
    request: RiskProfileRequest,
    user: CurrentUser,
    session: DBSession,
) -> dict:
    answers = request.answers.model_dump(mode="json")
    return success(
        await risk_profile_service.predict_and_store_risk_profile(
            session, user, answers
        )
    )


@router.get("")
async def get_risk_profile(user: CurrentUser, session: DBSession) -> dict:
    return success(await risk_profile_service.get_latest_risk_profile(session, user))
