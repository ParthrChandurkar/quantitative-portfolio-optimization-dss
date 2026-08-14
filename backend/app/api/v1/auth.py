from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import AppSettings, DBSession
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, SignupRequest
from app.schemas.common import success
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, session: DBSession, settings: AppSettings) -> dict:
    user, pair = await auth_service.signup(session, request, settings)
    return success(
        {"user": auth_service.user_payload(user), **auth_service.token_payload(pair)}
    )


@router.post("/login")
async def login(request: LoginRequest, session: DBSession, settings: AppSettings) -> dict:
    user, pair = await auth_service.login(
        session, str(request.email), request.password, settings
    )
    return success(
        {"user": auth_service.user_payload(user), **auth_service.token_payload(pair)}
    )


@router.post("/refresh")
async def refresh(
    request: RefreshRequest, session: DBSession, settings: AppSettings
) -> dict:
    pair = await auth_service.rotate_refresh_token(
        session, request.refresh_token, settings
    )
    return success(auth_service.token_payload(pair))


@router.post("/logout")
async def logout(
    request: LogoutRequest, session: DBSession, settings: AppSettings
) -> dict:
    await auth_service.logout(session, request.refresh_token, settings)
    return success({"logged_out": True})
