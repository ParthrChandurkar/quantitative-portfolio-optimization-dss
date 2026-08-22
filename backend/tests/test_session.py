from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.db import session as session_module


class _SessionContext:
    def __init__(self) -> None:
        self.session = AsyncMock()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args) -> None:
        return None


async def test_get_session_commits_after_success(monkeypatch) -> None:
    context = _SessionContext()
    monkeypatch.setattr(session_module, "AsyncSessionFactory", lambda: context)

    yielded = [item async for item in session_module.get_session()]

    assert yielded == [context.session]
    context.session.commit.assert_awaited_once()
    context.session.rollback.assert_not_awaited()


async def test_get_session_rolls_back_after_failure(monkeypatch) -> None:
    context = _SessionContext()
    monkeypatch.setattr(session_module, "AsyncSessionFactory", lambda: context)
    generator = session_module.get_session()
    assert await anext(generator) is context.session

    with pytest.raises(RuntimeError, match="request failed"):
        await generator.athrow(RuntimeError("request failed"))

    context.session.rollback.assert_awaited_once()
