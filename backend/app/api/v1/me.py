from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DBSession
from app.schemas.common import success
from app.schemas.users import UserUpdateRequest
from app.services import auth_service

router = APIRouter(tags=["me"])


@router.get("/me")
async def get_me(user: CurrentUser) -> dict:
    return success(auth_service.user_payload(user))


@router.patch("/me")
async def update_me(
    request: UserUpdateRequest, user: CurrentUser, session: DBSession
) -> dict:
    updated = await auth_service.update_profile(session, user, request)
    return success(auth_service.user_payload(updated))
