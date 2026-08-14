"""Argon2 password security and typed JWT access/refresh tokens."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings

JWT_ALGORITHM = "HS256"
password_hasher = PasswordHasher()


@dataclass(frozen=True, slots=True)
class TokenPayload:
    user_id: uuid.UUID
    token_type: Literal["access", "refresh"]
    token_id: uuid.UUID
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _encode_token(
    user_id: uuid.UUID,
    token_type: Literal["access", "refresh"],
    expires_at: datetime,
    secret: str,
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": token_type,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": expires_at,
        },
        secret,
        algorithm=JWT_ALGORITHM,
    )


def create_token_pair(user_id: uuid.UUID, settings: Settings) -> TokenPair:
    now = datetime.now(UTC)
    access_expiry = now + timedelta(seconds=settings.jwt_access_expiry)
    refresh_expiry = now + timedelta(seconds=settings.jwt_refresh_expiry)
    return TokenPair(
        _encode_token(user_id, "access", access_expiry, settings.jwt_secret),
        _encode_token(user_id, "refresh", refresh_expiry, settings.jwt_secret),
        access_expiry,
        refresh_expiry,
    )


def decode_token(
    token: str,
    settings: Settings,
    expected_type: Literal["access", "refresh"],
) -> TokenPayload:
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "type", "jti", "exp"]},
    )
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return TokenPayload(
        user_id=uuid.UUID(str(payload["sub"])),
        token_type=expected_type,
        token_id=uuid.UUID(str(payload["jti"])),
        expires_at=datetime.fromtimestamp(float(payload["exp"]), UTC),
    )


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
