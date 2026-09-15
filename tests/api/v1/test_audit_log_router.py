from datetime import datetime, timezone

URL = "/api/v1/audit-logs"


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def test_get_audit_logs_returns_calls_in_range(client, auth):
    await client.get("/api/v1/health/check")

    response = await client.get(URL, params={"start_date": today(), "end_date": today()}, headers=auth("root", "admin"))

    assert response.status_code == 200
    health_logs = [log for log in response.json() if log["action"] == "health_check"]
    assert len(health_logs) == 1
    assert health_logs[0]["endpoint"] == "/api/v1/health/check"
    assert health_logs[0]["status"] == "success"


async def test_get_audit_logs_outside_range_is_empty(client, auth):
    await client.get("/api/v1/health/check")

    response = await client.get(URL, params={"start_date": "2000-01-01", "end_date": "2000-01-02"}, headers=auth("root", "admin"))

    assert response.status_code == 200
    assert response.json() == []


async def test_get_audit_logs_requires_token(client):
    response = await client.get(URL, params={"start_date": today(), "end_date": today()})

    assert response.status_code == 401


async def test_get_audit_logs_requires_admin_role(client, auth):
    response = await client.get(URL, params={"start_date": today(), "end_date": today()}, headers=auth("alice"))

    assert response.status_code == 403


async def test_get_audit_logs_rejects_end_before_start(client, auth):
    response = await client.get(URL, params={"start_date": today(), "end_date": "2000-01-01"}, headers=auth("root", "admin"))

    assert response.status_code == 400
    assert response.json()["error"] == "InvalidInputError"


async def test_get_audit_logs_rejects_malformed_date(client, auth):
    response = await client.get(URL, params={"start_date": "15-09-2026", "end_date": today()}, headers=auth("root", "admin"))

    assert response.status_code == 422
