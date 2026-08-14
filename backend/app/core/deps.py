"""FastAPI request dependencies for database sessions and bearer authentication."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import APIError
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_session

bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise APIError(401, "AUTH_REQUIRED", "A valid bearer access token is required")
    try:
        payload = decode_token(credentials.credentials, settings, "access")
    except (jwt.PyJWTError, ValueError):
        raise APIError(401, "INVALID_TOKEN", "The access token is invalid or expired") from None
    user = await session.get(User, payload.user_id)
    if user is None:
        raise APIError(401, "INVALID_TOKEN", "The access token user no longer exists")
    return user


DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AppSettings = Annotated[Settings, Depends(get_settings)]
