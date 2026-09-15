# Base API - FastAPI Boilerplate

Modular template for REST APIs built with FastAPI on a strict layered architecture (Router → Service → Repository → Storage). MongoDB is the default storage backend; PostgreSQL is supported through the same storage interface.

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.141 | Async web framework |
| Pydantic / pydantic-settings | 2.13 / 2.15 | Validation and settings |
| MongoDB | 6 | Default database |
| PyMongo (async API) | 4.18 | MongoDB driver |
| PostgreSQL + asyncpg | - | Alternative backend (reference example) |
| httpx | 0.28 | HTTP client for external integrations |
| pytest + pytest-asyncio | 9.1 / 1.4 | Endpoint and architecture tests |
| Docker | - | Containerization |

Versions are pinned in `requirements.txt` / `requirements-dev.txt`.

---

## Quick Start

```bash
cp .env.example .env    # optional: every value has a default
docker-compose up -d
```

- REST API: `http://localhost:${API_PORT}/api/v1` (default `5008`)
- Swagger UI: `http://localhost:${API_PORT}/docs`
- Mongo Express: `http://localhost:8081` (admin/admin)

Tests (no database needed):

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Architecture — MANDATORY Layered Pattern

**Every feature MUST follow the Schema / Model / Router / Service / Repository pattern. No exceptions.**

```
                 Schemas (API contract)
                         ↕
Router (HTTP) → Service (business logic) → Repository (entity data access) → Storage (driver) → Database
                         │                          ↕
                         │                   Models (InDB)
                         └──→ Integration (external APIs)
```

| Layer | Folder | Does | NEVER does |
|-------|--------|------|------------|
| **Schema** | `app/schemas` | API contract: `Create`, `Update`, `Response` | Logic, persistence fields |
| **Model** | `app/models` | Persistence shape: `{Feature}InDB` | Logic, API concerns |
| **Router** | `app/api/v1` | HTTP input/output, calls its service | Business logic, data access, returning `InDB` models |
| **Service** | `app/services` | Business logic, `InDB` → `Response` conversion | Storage/driver access, filters, `HTTPException` |
| **Repository** | `app/repositories` | Typed data access for one entity, owns every query/filter | Business logic, HTTP, driver imports |
| **Storage** | `app/db` | Driver code behind `BaseStorage` (dicts in/out) | Anything entity-specific |
| **Integration** | `app/integrations` | Connectors to external services (payments, email, AI, ...) | Business logic, data access |
| **Decorators** | `app/decorators` | Endpoint cross-cutting concerns: errors, audit, auth | Business logic, data access |
| **Jobs** | `app/jobs` | Background job handlers (`@job`) and the worker runner | Data access, HTTP (handlers call services only) |

**Rules you must never break:**

1. A router only calls its service. It imports from `app.schemas`, `app.services` and `app.decorators`, never from `app.models`, `app.repositories` or `app.db`.
2. **A service accesses data only through entity repositories** (`app/repositories`). It never imports `app.db`, `get_storage()`, or a driver.
3. Services call only **public** repository methods. Every filter (`{"field": {"$gte": ...}}`) is written inside a repository method, never in a service.
4. Driver code (`pymongo`, `asyncpg`) lives only in `app/db`. `bson.ObjectId` is allowed only there and in `app/models` (through `PyObjectId`).
5. External HTTP calls live only in `app/integrations`; services get clients from factories and never import `httpx`.
6. Services raise exceptions from `app/core/exceptions.py`, never `HTTPException`: they must also work outside an HTTP request.
7. Models and schemas are pure data structures.
8. Skipping a layer is forbidden, even for "simple" endpoints.
9. Every endpoint has `@handle_errors` and `@audit_log`, in this order; protected endpoints add `@require_auth` right after them (see [Decorators](#decorators)).
10. Work that does not fit in a request runs as a background job: the endpoint enqueues it through a service, the handler in `app/jobs` calls services only (see [Background Jobs](#background-jobs)).

**These rules are enforced by [tests/test_architecture.py](tests/test_architecture.py). Run `pytest` after every change. If it fails, fix the code, never the test.**

## Project Structure

```
app/
├── api/
│   └── v1/
│       ├── __init__.py        # api_router: registers every v1 router
│       ├── health_router.py
│       ├── audit_log_router.py
│       ├── job_router.py      # GET /jobs, GET /jobs/{id}, POST /jobs/{id}/cancel
│       └── timer_router.py    # demo: POST /timers starts a job
├── core/
│   ├── config.py              # Settings (env vars)
│   ├── exceptions.py          # AppError and subclasses (400, 401, 403, 404, 502)
│   └── logging_config.py      # setup_logging()
├── decorators/                # Endpoint decorators
│   ├── __init__.py            # from app.decorators import handle_errors, audit_log, require_auth
│   ├── _signature.py          # Helper for parameters injected by FastAPI
│   ├── audit_log.py           # @audit_log
│   ├── auth.py                # @require_auth
│   └── error_handler.py       # @handle_errors
├── db/                        # Storage layer (driver-specific)
│   ├── database.py            # Connection lifecycle, get_storage(), ping_database()
│   ├── base_storage.py        # Abstract BaseStorage interface
│   ├── mongo_storage.py       # MongoDB implementation (active)
│   └── postgres_storage.py    # PostgreSQL implementation (reference example)
├── integrations/
│   └── clients.py             # Shared HTTP client lifecycle + connector factories
├── jobs/                      # Background jobs (run by the worker)
│   ├── __init__.py            # imports every job module so handlers get registered
│   ├── registry.py            # @job decorator
│   ├── context.py             # JobContext: progress, checkpoint, cancellation
│   ├── runner.py              # worker loop: claim, run, retry, recover
│   └── timer_job.py           # demo handler
├── models/                    # Persistence models ({Feature}InDB)
│   ├── base.py                # PyObjectId, utc_now
│   ├── audit_log.py
│   └── job.py                 # JobInDB, JobStatus
├── repositories/              # Entity repositories
│   ├── entity_repository.py   # Generic typed base class
│   ├── audit_log_repository.py
│   ├── health_repository.py
│   └── job_repository.py
├── schemas/                   # API contract (Create/Update/Response)
│   ├── audit_log.py
│   ├── auth.py                # AuthUser
│   ├── error.py
│   ├── health.py
│   └── job.py                 # JobResponse
├── services/
│   ├── audit_log_service.py
│   ├── auth_service.py        # Token → AuthUser: implement _verify_token()
│   ├── health_service.py
│   ├── job_service.py         # enqueue/get/cancel (API) + claim/retry (worker)
│   └── timer_service.py
├── main.py                    # API entry point: logging, lifespan, CORS, routers
└── worker.py                  # Worker entry point: python -m app.worker
tests/
├── conftest.py                # Fixtures: client, auth, in-memory storage
├── memory_storage.py          # In-memory BaseStorage
├── test_architecture.py       # Layers, decorators, every endpoint tested
└── api/v1/test_*_router.py    # One test file per router
```

---

## Repositories

Data access has two levels. Services only see the first.

### Entity repositories (`app/repositories`)

One repository per entity. It extends `EntityRepository[ModelT]` ([entity_repository.py](app/repositories/entity_repository.py)), takes and returns `{Feature}InDB` models, and exposes **domain methods** named after what they mean (`find_by_email`, `find_by_time_range`), never generic query methods.

| Method | Visibility | Use |
|--------|------------|-----|
| `get_by_id(id)` | public | `Optional[ModelT]` (None also for invalid ids) |
| `create(entity)` | public | Insert, returns the entity |
| `update(id, fields)` | public | Set fields, `False` if the entity does not exist |
| `delete(id)` | public | `False` if the entity does not exist |
| `_find_one(filters)`, `_find_many(filters, limit, skip, sort)`, `_count(filters)`, `_exists(filters)`, `_update(id, fields, where)`, `_update_many(filters, fields)`, `_claim_one(filters, fields, sort)` | protected | Building blocks for domain methods, used **only inside the repository** |

```python
class AuditLogRepository(EntityRepository[AuditLogInDB]):
    """Data access for audit logs."""

    collection = "audit_logs"
    model = AuditLogInDB

    async def find_by_time_range(self, start: datetime, end: datetime, limit: int = 100, skip: int = 0) -> List[AuditLogInDB]:
        """Logs with start <= timestamp < end, newest first."""
        return await self._find_many(
            {"timestamp": {"$gte": start, "$lt": end}},
            limit=limit, skip=skip, sort=[("timestamp", -1)]
        )


audit_log_repository = AuditLogRepository()
```

Entity repositories are backend-agnostic: they never import drivers or a concrete storage class. A feature with no persisted entity still gets a repository for whatever it reads (see [health_repository.py](app/repositories/health_repository.py), which only pings the database).

Filters use Mongo-style syntax, supported by both backends: equality plus `$gt`, `$gte`, `$lt`, `$lte`, `$ne`, `$in`.

**Indexes and retention** are declared on the repository and created at API startup:

```python
indexes = [
    Index([("status", 1), ("run_after", 1)]),                     # a query the repository runs often
    Index([("timestamp", 1)], expire_after_seconds=90 * 86400),   # retention: delete after 90 days
]
```

Add an index for every filter/sort a domain method uses on a growing collection. Retention (`expire_after_seconds`, single date field) is automatic on MongoDB; PostgreSQL has no expiry and logs a warning. Retention periods come from `Settings` (`AUDIT_LOG_RETENTION_DAYS`, `JOB_RETENTION_DAYS`); changing one later requires dropping the existing index.

### Storage (`app/db`)

`BaseStorage` ([base_storage.py](app/db/base_storage.py)) is the driver-level interface for one collection/table: plain dicts in and out, string ids. Only `EntityRepository` uses it, through `get_storage(collection)` in [database.py](app/db/database.py).

```python
class BaseStorage(ABC):
    async def find_one(self, id: str) -> Optional[Dict[str, Any]]: ...
    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    async def find_many(self, filters, limit=100, skip=0, sort=None) -> List[Dict[str, Any]]: ...
    async def count(self, filters: Dict[str, Any]) -> int: ...
    async def exists(self, filters: Dict[str, Any]) -> bool: ...
    async def insert_one(self, data: Dict[str, Any]) -> str: ...
    async def insert_many(self, data: List[Dict[str, Any]]) -> List[str]: ...
    async def update_one(self, id: str, data, where=None) -> bool: ...        # True if it exists and matches `where`
    async def update_many(self, filters, data) -> int: ...                   # matched documents
    async def claim_one(self, filters, data, sort=None) -> Optional[Dict]: ... # atomic update + return (job queue)
    async def ensure_index(self, fields, expire_after_seconds=None) -> None: ... # idempotent
    async def delete_one(self, id: str) -> bool: ...
    async def delete_many(self, filters: Dict[str, Any]) -> int: ...
```

- **`MongoStorage`** ([mongo_storage.py](app/db/mongo_storage.py)): PyMongo async API, documents stored as-is with `_id: ObjectId`. **Active backend.** The client is `tz_aware`, so datetimes come back as UTC-aware.
- **`PostgresStorage`** ([postgres_storage.py](app/db/postgres_storage.py)): **reference example, not wired in.** Each collection is a table `(id TEXT PRIMARY KEY, data JSONB)` created on first use. Numbers compare numerically, other values as text (datetimes in ISO format, all UTC). Table and field names must be plain identifiers.

Adding a backend = one new `{db}_storage.py` implementing `BaseStorage` + changes in `database.py`. Nothing else changes.

---

## Integrations

Connectors to external services live in `app/integrations`, one folder per capability (`geocoding/`, `payments/`, ...). The boilerplate ships only the shared HTTP client ([clients.py](app/integrations/clients.py)), opened and closed in the app and worker lifespan.

To add a connector:

1. `app/integrations/{capability}/base_{capability}_client.py`: abstract interface, plain dicts in/out (no SDK types).
2. `app/integrations/{capability}/{provider}_client.py`: implementation using `get_http_client()`; every provider failure becomes `ExternalServiceError` (502).
3. A factory in `clients.py`: the only place that knows which provider is active.
4. Configuration (API keys, base URLs) in `Settings`.

```python
# app/integrations/geocoding/nominatim_client.py
class NominatimClient(BaseGeocodingClient):
    """Geocoding through OpenStreetMap Nominatim."""

    def __init__(self, http: httpx.AsyncClient, base_url: str):
        self.http = http
        self.base_url = base_url

    async def geocode(self, address: str) -> Dict[str, Any]:
        try:
            response = await self.http.get(f"{self.base_url}/search", params={"q": address, "format": "json", "limit": 1})
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ExternalServiceError(f"Geocoding failed: {type(e).__name__}") from e
        results = response.json()
        return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])} if results else {}


# app/integrations/clients.py
def get_geocoding_client() -> BaseGeocodingClient:
    return NominatimClient(get_http_client(), base_url=settings.GEOCODING_BASE_URL)


# app/services/store_service.py: services only use the factory
location = await get_geocoding_client().geocode(data.address)
```

---

## Decorators

Endpoints use the decorators from [app/decorators](app/decorators), in this order (checked by the architecture test):

```python
@router.get("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
@handle_errors                                  # mandatory
@audit_log(metadata={"service": "products"})    # mandatory
@require_auth(roles=["admin"])                  # optional: protected endpoints only
async def get_product(product_id: str) -> ProductResponse:
    ...
```

### @handle_errors

Converts exceptions raised by the endpoint into responses with body `{"error": "<ExceptionClass>", "message": "..."}`. Services raise exceptions from [app/core/exceptions.py](app/core/exceptions.py):

| Exception | Status |
|-----------|--------|
| `UnauthorizedError` | 401 (with `WWW-Authenticate: Bearer`) |
| `ForbiddenError` | 403 |
| `NotFoundError` | 404 |
| `InvalidInputError` | 400 |
| `ExternalServiceError` | 502 |
| `ServiceUnavailableError` | 503 |
| Any other `AppError` | 400 |
| `HTTPException` | passed through unchanged |
| Unexpected exception | 500, generic message; traceback in the log, never in the response |
| Request validation (FastAPI) | 422 |

To add an error type: subclass `AppError` and add it to `_STATUS_CODES` in `error_handler.py`.

### @audit_log

Records every call in the `audit_logs` collection: `action` (function name), `endpoint` (request path), `method`, `status` (`success`/`error`), `duration_ms`, `timestamp` (UTC), `user_id` (with `@require_auth`), `metadata` (the dict passed to the decorator, plus `error` on failure).

Method and path are read from the request, which the decorator gets through a hidden parameter added to the endpoint signature. A failure while writing the log is logged and never affects the response.

`@audit_log(enabled=False)` keeps the mandatory decorator but records nothing: only for very frequent technical calls such as the health probes.

### @require_auth

```python
@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(metadata={"service": "users"})
@require_auth(roles=["admin", "editor"])    # any of these roles; require_auth() = any authenticated user
async def get_me(current_user: AuthUser) -> UserResponse:
    """Current user profile."""
    return await user_service.get_profile(current_user)
```

- Reads `Authorization: Bearer <token>` and resolves it with `auth_service.authenticate()`: missing or invalid token → 401, none of the required roles → 403.
- Declare `current_user: AuthUser` (from `app.schemas.auth`) only when the endpoint needs the user: the decorator fills it and hides it from the API. Pass it to the service as a normal argument.
- Swagger shows a lock and the **Authorize** button on protected endpoints.
- The user id ends up in the audit log, rejected (403) calls included.

## Authentication

The structure is fixed: the only thing to implement is **`AuthService._verify_token()`** in [auth_service.py](app/services/auth_service.py), which turns a token into `AuthUser(id, roles)` or raises `UnauthorizedError`. Until it is implemented every real token is rejected (401).

It is a service, so it can verify the token through an integration client (Firebase, any JWT/OIDC provider) and load roles through a repository. Provider-specific logic never goes into `@require_auth`.

### Mock tokens (local testing)

With `AUTH_MOCK_ENABLED=true` the API also accepts mock bearer tokens, so protected endpoints can be tested before the real implementation exists:

| Token | User | Roles |
|-------|------|-------|
| `mock:alice` | `alice` | none |
| `mock:alice:admin` | `alice` | `admin` |
| `mock:bob:admin,editor` | `bob` | `admin`, `editor` |

```bash
curl -H "Authorization: Bearer mock:bob:admin" \
  "http://localhost:5008/api/v1/audit-logs?start_date=2026-01-01&end_date=2026-12-31"
```

In Swagger click **Authorize** and paste the token without `Bearer`. The flag is off by default and logs a warning at startup: never enable it in production.

## Logging

`setup_logging()` ([logging_config.py](app/core/logging_config.py)) runs at startup and configures the `app` logger: stderr, format `timestamp LEVEL [logger.name] message`, level from `LOG_LEVEL`. Uvicorn and third-party loggers are left untouched.

In any module under `app/`:

```python
import logging

logger = logging.getLogger(__name__)
```

Never use `print`, and never log secrets (API keys, tokens, passwords, full LLM prompts with user data).

## Background Jobs

Long work runs in the **worker** (`python -m app.worker`, service `base-worker` in docker-compose), a separate process that uses the `jobs` collection as its queue. No extra infrastructure: scale by starting more workers.

**Flow:** endpoint → service → `job_service.enqueue(domain, job_type, payload, user_id)` → 202 with the job → the worker claims it atomically and runs its handler → the client follows `GET /api/v1/jobs/{id}`.

A job has a `domain` (e.g. `pdf`) and a `type` (e.g. `ingestion`): `GET /jobs?domain=pdf&status=running` lists them. Users see their own jobs, `admin` sees all. `resource_id` can link a job to the entity it works on.

### Adding a job

1. Handler in `app/jobs/{name}_job.py`, then import the module in [app/jobs/__init__.py](app/jobs/__init__.py):

```python
@job(domain="pdf", type="ingestion", max_attempts=3, timeout_seconds=1800)
async def ingest_pdf(payload: Dict[str, Any], ctx: JobContext) -> Dict[str, Any]:
    """Extract and index a PDF."""
    pages = await pdf_service.extract_pages(payload["document_id"])
    for i, page in enumerate(pages, start=1):
        await ctx.check_cancelled()                       # stop here if cancelled
        await pdf_service.index_page(payload["document_id"], page)
        await ctx.progress(i / len(pages) * 100, f"{i}/{len(pages)} pages")
    return {"pages": len(pages)}                          # saved as job result
```

2. Enqueue it from the feature service (never a generic "create job" endpoint):

```python
async def request_ingestion(self, document_id: str, user: AuthUser) -> JobResponse:
    return await job_service.enqueue("pdf", "ingestion", {"document_id": document_id}, user_id=user.id, resource_id=document_id)
```

3. The endpoint returns `JobResponse` with `status_code=status.HTTP_202_ACCEPTED`. See the demo: [timer_router.py](app/api/v1/timer_router.py) → [timer_service.py](app/services/timer_service.py) → [timer_job.py](app/jobs/timer_job.py).

### Handler rules

- Call **services only** (never repositories, `app.db` or integrations directly). Payload and result are small JSON dicts: store large outputs in their own entity.
- Call `ctx.check_cancelled()` between steps: cancellation is cooperative.
- For long workflows save checkpoints with `ctx.save_state({...})` and resume from `ctx.state`: after a crash the job restarts from there.
- Handlers may run more than once (retries, crashes): make each step safe to repeat.

### What the worker handles

| Situation | Behavior |
|-----------|----------|
| Exception | Retry with backoff (5s, 10s, 20s… max 5 min) until `max_attempts`, then `failed` with `error` |
| Timeout (`timeout_seconds`) | Counted as a failed attempt |
| Cancel on a pending job | `cancelled` immediately |
| Cancel on a running job | `cancel_requested`, the handler stops at the next `check_cancelled()`; a failure after the request ends `cancelled`, never retried |
| Worker crash | The job lock (`WORKER_LOCK_SECONDS`) expires: the job goes back to `pending` and resumes from its checkpoint, or ends `cancelled` if cancellation was requested |
| Lock lost (worker paused or cut off longer than the lock) | The next lock renewal fails and the handler is stopped: the job belongs to whoever claimed it |
| Unknown `domain`/`type` | `failed` ("No handler registered") |
| SIGTERM | No new jobs are claimed; running ones finish (or are recovered after the lock expires) |

Statuses: `pending` → `running` → `succeeded` | `failed` | `cancelled`.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Tests never touch a real database or network. [tests/conftest.py](tests/conftest.py) gives every test a fresh in-memory storage and enables mock auth tokens.

| Fixture | Use |
|---------|-----|
| `client` | `httpx.AsyncClient` calling the app in-process: `await client.get("/api/v1/...")` |
| `auth(user_id, *roles)` | Mock bearer header: `headers=auth("alice", "admin")` |
| `storage` | `{collection: MemoryStorage}` behind every repository (automatic) |

### Endpoint test rules

1. **One file per router**, same path: `app/api/v1/product_router.py` → `tests/api/v1/test_product_router.py`.
2. **Test through HTTP** with `client`, never by calling services directly. Use repositories only to arrange data the API cannot create (e.g. a job already running).
3. **No real database or network**: replace connectors with fakes where the service imports the factory, e.g. `monkeypatch.setattr("app.services.store_service.get_geocoding_client", lambda: FakeGeocodingClient())`.
4. **Every endpoint covers**, when applicable:
   - success: status code and the relevant body fields
   - invalid input: 422
   - protected endpoints: 401 without token, 403 without the role
   - business errors: 404, 400, ...
5. **Names**: `test_<endpoint_function>_<scenario>`, e.g. `test_get_job_of_another_user_is_not_found`.
6. **Independent tests**: each test arranges what it needs; no shared state, no order.
7. Plain `async def` tests (no decorator needed), laid out as arrange / act / assert.

The architecture test fails if a router has no test file or an endpoint has no `test_<endpoint>_*` test. Examples: [tests/api/v1](tests/api/v1).

---

## Switching to PostgreSQL

Services, repositories and routers never change. To enable `PostgresStorage`:

**1. `requirements.txt`**: add `asyncpg==0.31.0`.

**2. `app/core/config.py`**: add the setting (not present by default):

```python
    POSTGRES_URI: str = "postgresql://postgres:postgres@localhost:5432/base_api_db"
```

**3. `app/db/database.py`**: replace the MongoDB lifecycle, ping and factory:

```python
import asyncio
from typing import Optional

import asyncpg

from app.core.config import settings
from app.db.base_storage import BaseStorage
from app.db.postgres_storage import PostgresStorage

PING_TIMEOUT_SECONDS = 3


class Database:
    pg_pool: Optional[asyncpg.Pool] = None


db = Database()


async def db_connect() -> None:
    db.pg_pool = await asyncpg.create_pool(settings.POSTGRES_URI)


async def db_disconnect() -> None:
    if db.pg_pool:
        await db.pg_pool.close()


async def ping_database() -> bool:
    try:
        async with db.pg_pool.acquire() as conn:
            await asyncio.wait_for(conn.fetchval("SELECT 1"), PING_TIMEOUT_SECONDS)
        return True
    except Exception:
        return False


def get_storage(collection: str) -> BaseStorage:
    return PostgresStorage(db.pg_pool, collection)
```

**4. `docker-compose.yaml`**: add the database and point `base-api` at it (the Mongo services can be removed):

```yaml
services:
  base-api:
    # ...existing config...
    environment:
      - POSTGRES_URI=postgresql://postgres:postgres@base-postgres:5432/base_api_db
    depends_on:
      - base-postgres

  base-postgres:
    image: postgres:16
    container_name: base-postgres
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-postgres}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
      - POSTGRES_DB=${POSTGRES_DB:-base_api_db}
    volumes:
      - base_postgres_data:/var/lib/postgresql/data

volumes:
  base_postgres_data:
```

**5.** `docker-compose up -d --build`

---

## Naming Conventions

| Type | File | Class / instance |
|------|------|------------------|
| Model | `app/models/{feature}.py` | `{Feature}InDB` |
| Schemas | `app/schemas/{feature}.py` | `{Feature}Create`, `{Feature}Update`, `{Feature}Response` |
| Repository | `app/repositories/{feature}_repository.py` | `{Feature}Repository` / `{feature}_repository` |
| Service | `app/services/{feature}_service.py` | `{Feature}Service` / `{feature}_service` |
| Router | `app/api/v1/{feature}_router.py` | `router` |
| Storage | `app/db/{db}_storage.py` | `{Db}Storage` |
| Integration | `app/integrations/{capability}/{provider}_client.py` | `{Provider}Client` |
| Collection | plural snake_case | `products`, `audit_logs` |
| URL prefix | plural kebab-case | `/products`, `/audit-logs` |

Python: `snake_case` functions/variables/files, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.

---

## Adding a New Feature

Example: `Product`. **All steps are required.**

### 1. Model — `app/models/product.py`

```python
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import PyObjectId, utc_now


class ProductInDB(BaseModel):
    """Persistence model for the products collection."""
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: Optional[str] = None
    price: float
    category: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: Optional[datetime] = None
```

- Always `PyObjectId` with `alias="_id"` and `model_config = ConfigDict(populate_by_name=True)`.
- Timestamps with `default_factory=utc_now` (never `datetime.utcnow`/`datetime.now()`).
- Pydantic v2 only: no `class Config`, no `json_encoders`.

### 2. Schemas — `app/schemas/product.py`

```python
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """POST request body."""
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0)
    category: str
    tags: List[str] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """PATCH request body: only the fields sent are updated."""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ProductResponse(BaseModel):
    """API response model."""
    id: str
    name: str
    description: Optional[str]
    price: float
    category: str
    tags: List[str]
    created_at: datetime
    updated_at: Optional[datetime]
```

- Schemas never import from `app.models`. Routers never expose `InDB` models.

### 3. Repository — `app/repositories/product_repository.py`

```python
from typing import List, Optional

from app.models.product import ProductInDB
from app.repositories.entity_repository import EntityRepository


class ProductRepository(EntityRepository[ProductInDB]):
    """Data access for products."""

    collection = "products"
    model = ProductInDB

    async def find_by_category(
        self,
        category: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[ProductInDB]:
        """Products in a category (all if None), newest first."""
        filters = {"category": category} if category else {}
        return await self._find_many(filters, limit=limit, skip=skip, sort=[("created_at", -1)])

    async def exists_by_name(self, name: str) -> bool:
        return await self._exists({"name": name})


product_repository = ProductRepository()
```

- Set `collection` and `model`; add one domain method per query the service needs.
- Export a singleton. Never import drivers or `bson`.

### 4. Service — `app/services/product_service.py`

```python
from typing import List, Optional

from app.core.exceptions import InvalidInputError, NotFoundError
from app.models.base import utc_now
from app.models.product import ProductInDB
from app.repositories.product_repository import product_repository
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate


class ProductService:
    """Business logic for products."""

    async def create(self, data: ProductCreate) -> ProductResponse:
        """
        Create a product.

        Raises:
            InvalidInputError: If a product with the same name exists
        """
        if await product_repository.exists_by_name(data.name):
            raise InvalidInputError(f"Product '{data.name}' already exists")
        product = await product_repository.create(ProductInDB(**data.model_dump()))
        return self._to_response(product)

    async def get_by_id(self, product_id: str) -> ProductResponse:
        """Fetch a product. Raises NotFoundError if missing."""
        product = await product_repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return self._to_response(product)

    async def get_all(self, category: Optional[str], limit: int, skip: int) -> List[ProductResponse]:
        """Fetch products, optionally filtered by category."""
        products = await product_repository.find_by_category(category, limit=limit, skip=skip)
        return [self._to_response(p) for p in products]

    async def update(self, product_id: str, data: ProductUpdate) -> ProductResponse:
        """Update the fields sent. Raises NotFoundError if missing."""
        fields = data.model_dump(exclude_unset=True)
        fields["updated_at"] = utc_now()
        if not await product_repository.update(product_id, fields):
            raise NotFoundError("Product not found")
        return await self.get_by_id(product_id)

    async def delete(self, product_id: str) -> None:
        """Delete a product. Raises NotFoundError if missing."""
        if not await product_repository.delete(product_id):
            raise NotFoundError("Product not found")

    def _to_response(self, product: ProductInDB) -> ProductResponse:
        return ProductResponse(id=str(product.id), **product.model_dump(exclude={"id"}))


product_service = ProductService()
```

- One class per feature, exported as a singleton, all methods async.
- Returns `Response` schemas; converts with a private `_to_response()`.
- Business rules (uniqueness, ranges, permissions) live here; queries live in the repository.

### 5. Router — `app/api/v1/product_router.py`

```python
from typing import List, Optional

from fastapi import APIRouter, Query, status

from app.decorators import audit_log, handle_errors
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
@handle_errors
@audit_log(metadata={"service": "products"})
async def create_product(data: ProductCreate) -> ProductResponse:
    """Create a new product."""
    return await product_service.create(data)


@router.get("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(metadata={"service": "products"})
async def get_product(product_id: str) -> ProductResponse:
    """Fetch a product by id."""
    return await product_service.get_by_id(product_id)


@router.get("", response_model=List[ProductResponse], status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(metadata={"service": "products"})
async def get_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    skip: int = Query(0, ge=0, description="Results to skip")
) -> List[ProductResponse]:
    """Fetch products with optional filters."""
    return await product_service.get_all(category=category, limit=limit, skip=skip)


@router.patch("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(metadata={"service": "products"})
async def update_product(product_id: str, data: ProductUpdate) -> ProductResponse:
    """Update an existing product."""
    return await product_service.update(product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_errors
@audit_log(metadata={"service": "products"})
async def delete_product(product_id: str) -> None:
    """Delete a product."""
    await product_service.delete(product_id)
```

- `prefix` and `tags` always set; collection routes use `""`, not `"/"`.
- Always `response_model`, explicit `status.HTTP_*`, return type, docstring (shown in Swagger).
- Query params with `Query()` and a description; paginated lists take `limit` and `skip`.
- **Mandatory decorators**: `@router.<method>` → `@handle_errors` → `@audit_log(metadata={"service": "<feature>"})` → `async def`. Protected endpoints add `@require_auth(roles=[...])` right before `async def`.
- No try/except and no logic: the router only calls the service.

### 6. Register — `app/api/v1/__init__.py`

```python
from app.api.v1 import audit_log_router, health_router, product_router

api_router.include_router(product_router.router)
```

### 7. Tests — `tests/api/v1/test_product_router.py`

```python
URL = "/api/v1/products"
PEN = {"name": "Pen", "price": 2.5, "category": "office"}


async def create_product(client, **overrides) -> dict:
    response = await client.post(URL, json={**PEN, **overrides})
    assert response.status_code == 201
    return response.json()


async def test_create_product_returns_created_product(client):
    response = await client.post(URL, json=PEN)

    assert response.status_code == 201
    assert response.json()["name"] == "Pen"


async def test_create_product_duplicate_name_is_rejected(client):
    await create_product(client)

    response = await client.post(URL, json=PEN)

    assert response.status_code == 400


async def test_create_product_rejects_invalid_price(client):
    response = await client.post(URL, json={**PEN, "price": -1})

    assert response.status_code == 422


async def test_get_product_returns_product(client):
    product = await create_product(client)

    response = await client.get(f"{URL}/{product['id']}")

    assert response.status_code == 200
    assert response.json() == product


async def test_get_product_unknown_id_is_not_found(client):
    response = await client.get(f"{URL}/000000000000000000000000")

    assert response.status_code == 404


async def test_get_products_filters_by_category(client):
    await create_product(client)
    await create_product(client, name="Mug", category="kitchen")

    response = await client.get(URL, params={"category": "kitchen"})

    assert [p["name"] for p in response.json()] == ["Mug"]


async def test_update_product_changes_only_sent_fields(client):
    product = await create_product(client)

    response = await client.patch(f"{URL}/{product['id']}", json={"price": 3})

    assert response.status_code == 200
    assert response.json()["price"] == 3
    assert response.json()["name"] == "Pen"


async def test_update_product_unknown_id_is_not_found(client):
    response = await client.patch(f"{URL}/000000000000000000000000", json={"price": 3})

    assert response.status_code == 404


async def test_delete_product_removes_product(client):
    product = await create_product(client)

    response = await client.delete(f"{URL}/{product['id']}")

    assert response.status_code == 204
    assert (await client.get(f"{URL}/{product['id']}")).status_code == 404
```

Protected endpoints also get `..._requires_token` (401) and, with roles, `..._requires_<role>_role` (403) tests.

---

## Configuration

Settings live in [app/core/config.py](app/core/config.py) and are read from environment variables or `.env` (see [.env.example](.env.example)). Add new variables there with a default:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MY_NEW_VAR: str = "default_value"
```

### CORS

Disabled by default. To let a browser frontend on another origin call the API, set `CORS_ORIGINS` to a JSON list:

```env
CORS_ORIGINS='["http://localhost:5173"]'
```

`"*"` allows any origin but automatically disables credentials (cookies, `Authorization` sent by the browser).

### Retention

`AUDIT_LOG_RETENTION_DAYS` (default 90) and `JOB_RETENTION_DAYS` (default 30, from the job end) control how long audit logs and finished jobs are kept; `0` keeps them forever. See [Indexes and retention](#entity-repositories-apprepositories).

### Health probes

`GET /api/v1/health/live` answers 200 while the process runs (liveness: restart the container if it fails). `GET /api/v1/health/ready` answers 503 when the database is unreachable (readiness: stop sending traffic). Neither is audited.

## Docker

`docker-compose.yaml` is for development: it mounts the code and runs uvicorn with `--reload`. `base-worker` runs the same image with `python -m app.worker` and does not auto-reload: restart it after changing jobs or services (`docker-compose restart base-worker`). The `Dockerfile` alone builds a self-contained image (code copied, non-root user, no reload).

```bash
docker-compose up -d            # start
docker-compose up -d --build    # rebuild after dependency changes
docker-compose logs -f base-api # logs
docker-compose down [-v]        # stop [and remove volumes]
```

---

## Code Style

- **Imports**: standard library, third-party, local (`app.*`), separated by a blank line.
- **Type hints**: always complete, including return types.
- **Docstrings**: Google style for public methods (`Args`, `Returns`, `Raises` when useful).
- **Async**: every I/O operation is `async`/`await`.
- **Time**: always UTC-aware, via `utc_now()`.

## New Feature Checklist

- [ ] `app/models/{feature}.py`: `{Feature}InDB` with `PyObjectId` alias `_id`, `utc_now` timestamps
- [ ] `app/schemas/{feature}.py`: `Create`, `Update` (if needed), `Response`
- [ ] `app/repositories/{feature}_repository.py`: extends `EntityRepository`, domain methods, singleton
- [ ] `app/services/{feature}_service.py`: uses only public repository methods, raises `AppError` subclasses, singleton
- [ ] `app/api/v1/{feature}_router.py`: schemas only, `@handle_errors` + `@audit_log` (+ `@require_auth` if protected), `response_model` + `status_code`
- [ ] Router registered in `app/api/v1/__init__.py`
- [ ] `tests/api/v1/test_{feature}_router.py`: every endpoint tested (success, 422, 401/403, business errors)
- [ ] `pytest` passes

---

## Existing API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health/live` | Liveness: 200 while the process runs, with version and uptime |
| GET | `/api/v1/health/ready` | Readiness: 200 if the database is reachable, 503 otherwise |
| GET | `/api/v1/audit-logs` | Audit logs in a date range, newest first. Requires role `admin` |
| GET | `/api/v1/jobs` | Your jobs (all for `admin`), filters `domain`, `type`, `status`, `limit`, `skip` |
| GET | `/api/v1/jobs/{id}` | Job status, progress, result |
| POST | `/api/v1/jobs/{id}/cancel` | Cancel a pending or running job |
| POST | `/api/v1/timers?seconds=10` | Demo: start a timer job (202) |

`/audit-logs` query parameters: `start_date`, `end_date` (`YYYY-MM-DD`, inclusive, UTC), `limit` (1-1000, default 100), `skip` (default 0).

## License

MIT
