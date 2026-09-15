import pytest

URL = "/api/v1/timers"


async def test_start_timer_enqueues_pending_job(client, auth):
    response = await client.post(URL, params={"seconds": 5}, headers=auth("alice"))

    assert response.status_code == 202
    job = response.json()
    assert (job["domain"], job["type"], job["status"]) == ("demo", "timer", "pending")
    assert job["payload"] == {"seconds": 5}
    assert job["user_id"] == "alice"


async def test_start_timer_requires_token(client):
    response = await client.post(URL, params={"seconds": 5})

    assert response.status_code == 401


@pytest.mark.parametrize("seconds", [0, 3601, "abc"])
async def test_start_timer_rejects_invalid_seconds(client, auth, seconds):
    response = await client.post(URL, params={"seconds": seconds}, headers=auth("alice"))

    assert response.status_code == 422
