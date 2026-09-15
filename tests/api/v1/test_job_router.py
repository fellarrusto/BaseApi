from app.models.job import JobInDB, JobStatus
from app.repositories.job_repository import job_repository

URL = "/api/v1/jobs"
MISSING_ID = "000000000000000000000000"


async def start_timer(client, auth, user_id: str) -> dict:
    response = await client.post("/api/v1/timers", params={"seconds": 5}, headers=auth(user_id))
    assert response.status_code == 202
    return response.json()


async def create_job(user_id: str, status: str, domain: str = "demo", job_type: str = "timer") -> str:
    """Arrange jobs in states the API cannot produce without a worker."""
    job = await job_repository.create(JobInDB(domain=domain, type=job_type, status=status, user_id=user_id))
    return str(job.id)


# ----- GET /jobs -----

async def test_list_jobs_returns_only_own_jobs(client, auth):
    await start_timer(client, auth, "alice")
    await start_timer(client, auth, "bob")

    response = await client.get(URL, headers=auth("alice"))

    assert response.status_code == 200
    assert [job["user_id"] for job in response.json()] == ["alice"]


async def test_list_jobs_admin_sees_every_job(client, auth):
    await start_timer(client, auth, "alice")
    await start_timer(client, auth, "bob")

    response = await client.get(URL, headers=auth("root", "admin"))

    assert response.status_code == 200
    assert sorted(job["user_id"] for job in response.json()) == ["alice", "bob"]


async def test_list_jobs_filters_by_domain_type_and_status(client, auth):
    await start_timer(client, auth, "alice")
    await create_job("alice", JobStatus.SUCCEEDED)
    await create_job("alice", JobStatus.SUCCEEDED, domain="pdf", job_type="ingestion")

    response = await client.get(URL, params={"domain": "demo", "type": "timer", "status": "succeeded"}, headers=auth("alice"))

    assert response.status_code == 200
    assert [(job["domain"], job["type"], job["status"]) for job in response.json()] == [("demo", "timer", "succeeded")]


async def test_list_jobs_requires_token(client):
    response = await client.get(URL)

    assert response.status_code == 401


async def test_list_jobs_rejects_invalid_limit(client, auth):
    response = await client.get(URL, params={"limit": 0}, headers=auth("alice"))

    assert response.status_code == 422


# ----- GET /jobs/{id} -----

async def test_get_job_returns_job(client, auth):
    job = await start_timer(client, auth, "alice")

    response = await client.get(f"{URL}/{job['id']}", headers=auth("alice"))

    assert response.status_code == 200
    assert response.json()["id"] == job["id"]
    assert response.json()["status"] == "pending"


async def test_get_job_admin_can_read_any_job(client, auth):
    job = await start_timer(client, auth, "alice")

    response = await client.get(f"{URL}/{job['id']}", headers=auth("root", "admin"))

    assert response.status_code == 200


async def test_get_job_of_another_user_is_not_found(client, auth):
    job = await start_timer(client, auth, "alice")

    response = await client.get(f"{URL}/{job['id']}", headers=auth("bob"))

    assert response.status_code == 404


async def test_get_job_unknown_id_is_not_found(client, auth):
    response = await client.get(f"{URL}/{MISSING_ID}", headers=auth("alice"))

    assert response.status_code == 404
    assert response.json()["error"] == "NotFoundError"


async def test_get_job_requires_token(client):
    response = await client.get(f"{URL}/{MISSING_ID}")

    assert response.status_code == 401


# ----- POST /jobs/{id}/cancel -----

async def test_cancel_job_cancels_pending_job(client, auth):
    job = await start_timer(client, auth, "alice")

    response = await client.post(f"{URL}/{job['id']}/cancel", headers=auth("alice"))

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["finished_at"] is not None


async def test_cancel_job_asks_running_job_to_stop(client, auth):
    job_id = await create_job("alice", JobStatus.RUNNING)

    response = await client.post(f"{URL}/{job_id}/cancel", headers=auth("alice"))

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["cancel_requested"] is True


async def test_cancel_job_already_finished_is_rejected(client, auth):
    job_id = await create_job("alice", JobStatus.SUCCEEDED)

    response = await client.post(f"{URL}/{job_id}/cancel", headers=auth("alice"))

    assert response.status_code == 400
    assert response.json()["error"] == "InvalidInputError"


async def test_cancel_job_of_another_user_is_not_found(client, auth):
    job = await start_timer(client, auth, "alice")

    response = await client.post(f"{URL}/{job['id']}/cancel", headers=auth("bob"))

    assert response.status_code == 404


async def test_cancel_job_requires_token(client):
    response = await client.post(f"{URL}/{MISSING_ID}/cancel")

    assert response.status_code == 401
