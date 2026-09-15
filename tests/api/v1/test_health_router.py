import pytest

from app.repositories.health_repository import health_repository

LIVE_URL = "/api/v1/health/live"
READY_URL = "/api/v1/health/ready"


def database_reachable(monkeypatch: pytest.MonkeyPatch, reachable: bool) -> None:
    async def ping() -> bool:
        return reachable
    monkeypatch.setattr(health_repository, "ping", ping)


async def test_liveness_is_alive_even_without_database(client, monkeypatch):
    database_reachable(monkeypatch, False)

    response = await client.get(LIVE_URL)

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


async def test_liveness_is_not_audited(client, storage):
    await client.get(LIVE_URL)

    assert "audit_logs" not in storage or not storage["audit_logs"].docs


async def test_readiness_database_up(client, monkeypatch):
    database_reachable(monkeypatch, True)

    response = await client.get(READY_URL)

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}


async def test_readiness_database_down_is_unavailable(client, monkeypatch):
    database_reachable(monkeypatch, False)

    response = await client.get(READY_URL)

    assert response.status_code == 503
    assert response.json()["error"] == "ServiceUnavailableError"
