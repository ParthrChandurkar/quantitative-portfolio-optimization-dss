"""Account creation, login, refresh rotation, logout, and profile updates."""

from __future__ import annotations

from datetime import UTC, datetime

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import APIError
from app.core.security import (
    TokenPair,
    create_token_pair,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import RefreshToken, User
from app.schemas.auth import SignupRequest
from app.schemas.users import UserUpdateRequest


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "risk_profile_default": user.risk_profile_default,
        "created_at": user.created_at,
    }


def token_payload(pair: TokenPair) -> dict:
    return {
        "access_token": pair.access_token,
        "refresh_token": pair.refresh_token,
        "token_type": "bearer",
        "access_expires_at": pair.access_expires_at,
        "refresh_expires_at": pair.refresh_expires_at,
    }


async def _store_refresh(
    session: AsyncSession, user_id, pair: TokenPair
) -> RefreshToken:
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(pair.refresh_token),
        expires_at=pair.refresh_expires_at,
    )
    session.add(row)
    await session.flush()
    return row


async def signup(
    session: AsyncSession, request: SignupRequest, settings: Settings
) -> tuple[User, TokenPair]:
    email = str(request.email).strip().casefold()
    if await session.scalar(select(User.id).where(User.email == email)) is not None:
        raise APIError(409, "EMAIL_EXISTS", "An account with this email already exists")
    user = User(
        email=email,
        password_hash=hash_password(request.password),
        full_name=request.full_name.strip(),
    )
    session.add(user)
    await session.flush()
    pair = create_token_pair(user.id, settings)
    await _store_refresh(session, user.id, pair)
    await session.commit()
    await session.refresh(user)
    return user, pair


async def login(
    session: AsyncSession, email: str, password: str, settings: Settings
) -> tuple[User, TokenPair]:
    user = await session.scalar(select(User).where(User.email == email.strip().casefold()))
    if user is None or not verify_password(password, user.password_hash):
        raise APIError(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    pair = create_token_pair(user.id, settings)
    await _store_refresh(session, user.id, pair)
    await session.commit()
    return user, pair


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def rotate_refresh_token(
    session: AsyncSession, refresh_token: str, settings: Settings
) -> TokenPair:
    try:
        payload = decode_token(refresh_token, settings, "refresh")
    except (jwt.PyJWTError, ValueError):
        raise APIError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired") from None
    stored = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.user_id == payload.user_id,
            RefreshToken.token_hash == hash_refresh_token(refresh_token),
        )
    )
    now = datetime.now(UTC)
    if stored is None or stored.revoked_at is not None or _aware(stored.expires_at) <= now:
        raise APIError(401, "INVALID_REFRESH_TOKEN", "Refresh token is revoked or expired")
    pair = create_token_pair(payload.user_id, settings)
    replacement = await _store_refresh(session, payload.user_id, pair)
    stored.revoked_at = now
    stored.replaced_by_token_id = replacement.id
    await session.commit()
    return pair


async def logout(
    session: AsyncSession, refresh_token: str, settings: Settings
) -> None:
    try:
        payload = decode_token(refresh_token, settings, "refresh")
    except (jwt.PyJWTError, ValueError):
        raise APIError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired") from None
    stored = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.user_id == payload.user_id,
            RefreshToken.token_hash == hash_refresh_token(refresh_token),
        )
    )
    if stored is None or stored.revoked_at is not None:
        raise APIError(401, "INVALID_REFRESH_TOKEN", "Refresh token is already revoked")
    stored.revoked_at = datetime.now(UTC)
    await session.commit()


async def update_profile(
    session: AsyncSession, user: User, request: UserUpdateRequest
) -> User:
    if request.full_name is not None:
        user.full_name = request.full_name.strip()
    if "risk_profile_default" in request.model_fields_set:
        user.risk_profile_default = request.risk_profile_default
    await session.commit()
    await session.refresh(user)
    return user
