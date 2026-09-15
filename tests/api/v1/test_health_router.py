import pytest

from app.repositories.health_repository import health_repository

URL = "/api/v1/health/check"


def database_reachable(monkeypatch: pytest.MonkeyPatch, reachable: bool) -> None:
    async def ping() -> bool:
        return reachable
    monkeypatch.setattr(health_repository, "ping", ping)


async def test_health_check_database_up(client, monkeypatch):
    database_reachable(monkeypatch, True)

    response = await client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] == "up"


async def test_health_check_database_down(client, monkeypatch):
    database_reachable(monkeypatch, False)

    response = await client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "down"


async def test_health_check_is_public(client, monkeypatch):
    database_reachable(monkeypatch, True)

    response = await client.get(URL)

    assert response.status_code == 200
