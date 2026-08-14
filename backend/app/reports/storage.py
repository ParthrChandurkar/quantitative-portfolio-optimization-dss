"""Storage-neutral report artifact interface and local implementation."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredObject:
    location: str
    download_url: str
    size_bytes: int


class ReportStorage(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> StoredObject:
        """Persist bytes and return an opaque location plus client download URL."""

    async def get(self, location: str) -> bytes:
        """Read bytes from an opaque location returned by ``put``."""

    def url_for(self, location: str) -> str:
        """Return the client-facing download URL for a stored location."""


class LocalDiskStorage:
    def __init__(self, root: Path, url_prefix: str = "/generated-reports") -> None:
        self._root = root.resolve()
        self._url_prefix = url_prefix.rstrip("/")

    def _target(self, key: str) -> Path:
        relative = PurePosixPath(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("storage key must be a safe relative path")
        target = self._root.joinpath(*relative.parts).resolve()
        if self._root != target and self._root not in target.parents:
            raise ValueError("storage key escapes configured root")
        return target

    def _write(self, key: str, content: bytes) -> None:
        target = self._target(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f"{target.suffix}.tmp")
        temporary.write_bytes(content)
        temporary.replace(target)

    async def put(self, key: str, content: bytes, content_type: str) -> StoredObject:
        if content_type != "application/pdf":
            raise ValueError("local report storage accepts PDF content only")
        await asyncio.to_thread(self._write, key, content)
        return StoredObject(
            location=key,
            download_url=f"{self._url_prefix}/{key}",
            size_bytes=len(content),
        )

    async def get(self, location: str) -> bytes:
        target = self._target(location)
        if not target.is_file():
            raise FileNotFoundError(location)
        return await asyncio.to_thread(target.read_bytes)

    def url_for(self, location: str) -> str:
        self._target(location)
        return f"{self._url_prefix}/{location}"


def default_storage() -> ReportStorage:
    root = Path(os.getenv("REPORT_STORAGE_ROOT", "generated-reports"))
    return LocalDiskStorage(root)
