from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class Envelope(BaseModel, Generic[T]):
    data: T | None
    error: ErrorDetail | None


def success(data: T) -> dict[str, T | None]:
    return {"data": data, "error": None}
