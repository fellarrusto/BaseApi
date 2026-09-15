"""Shared test fixtures: in-memory storage, HTTP client, mock auth."""
import os
from typing import AsyncIterator, Callable, Dict

import httpx
import pytest

# Settings are read when the app is imported: configure the test environment first
os.environ["AUTH_MOCK_ENABLED"] = "true"
os.environ["CORS_ORIGINS"] = "[]"

from app.main import app  # noqa: E402
from app.repositories.entity_repository import EntityRepository  # noqa: E402
from tests.memory_storage import MemoryStorage  # noqa: E402


@pytest.fixture(autouse=True)
def storage(monkeypatch: pytest.MonkeyPatch) -> Dict[str, MemoryStorage]:
    """Fresh in-memory storage for every test: {collection name: MemoryStorage}."""
    collections: Dict[str, MemoryStorage] = {}
    monkeypatch.setattr(
        EntityRepository,
        "_storage",
        property(lambda repo: collections.setdefault(repo.collection, MemoryStorage()))
    )
    return collections


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client calling the app in-process (no server, no lifespan, no database)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
def auth() -> Callable[..., Dict[str, str]]:
    """auth("alice", "admin") -> Authorization header with a mock token for alice with role admin."""
    def headers(user_id: str, *roles: str) -> Dict[str, str]:
        token = f"mock:{user_id}:{','.join(roles)}" if roles else f"mock:{user_id}"
        return {"Authorization": f"Bearer {token}"}
    return headers
