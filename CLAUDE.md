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
| pytest | 9.1 | Architecture tests |
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

Architecture tests (no database needed):

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
| **Integration** | `app/integrations` | Connectors to external services (LLM, APIs) | Business logic, data access |

**Rules you must never break:**

1. A router only calls its service. It imports from `app.schemas` and `app.services`, never from `app.models`, `app.repositories` or `app.db`.
2. **A service accesses data only through entity repositories** (`app/repositories`). It never imports `app.db`, `get_storage()`, or a driver.
3. Services call only **public** repository methods. Every filter (`{"field": {"$gte": ...}}`) is written inside a repository method, never in a service.
4. Driver code (`pymongo`, `asyncpg`) lives only in `app/db`. `bson.ObjectId` is allowed only there and in `app/models` (through `PyObjectId`).
5. External HTTP calls live only in `app/integrations`; services get clients from factories and never import `httpx`.
6. Services raise exceptions from `app/core/exceptions.py`, never `HTTPException`: they must also work outside an HTTP request.
7. Models and schemas are pure data structures.
8. Skipping a layer is forbidden, even for "simple" endpoints.
9. Every endpoint has `@handle_errors` and `@audit_log`, in this order (see [Decorators](#decorators)).

**These rules are enforced by [tests/test_architecture.py](tests/test_architecture.py). Run `pytest` after every change. If it fails, fix the code, never the test.**

## Project Structure

```
app/
├── api/
│   └── v1/
│       ├── __init__.py        # api_router: registers every v1 router
│       ├── health_router.py
│       └── audit_log_router.py
├── core/
│   ├── config.py              # Settings (env vars)
│   ├── decorator.py           # @handle_errors, @audit_log
│   ├── exceptions.py          # AppError, NotFoundError, InvalidInputError, ExternalServiceError
│   └── logging_config.py      # setup_logging()
├── db/                        # Storage layer (driver-specific)
│   ├── database.py            # Connection lifecycle, get_storage(), ping_database()
│   ├── base_storage.py        # Abstract BaseStorage interface
│   ├── mongo_storage.py       # MongoDB implementation (active)
│   └── postgres_storage.py    # PostgreSQL implementation (reference example)
├── integrations/
│   ├── clients.py             # Shared HTTP client lifecycle + client factories
│   └── llm/
│       ├── base_llm_client.py
│       └── openrouter_client.py
├── models/                    # Persistence models ({Feature}InDB)
│   ├── base.py                # PyObjectId, utc_now
│   └── audit_log.py
├── repositories/              # Entity repositories
│   ├── entity_repository.py   # Generic typed base class
│   ├── audit_log_repository.py
│   └── health_repository.py
├── schemas/                   # API contract (Create/Update/Response)
│   ├── audit_log.py
│   ├── error.py
│   └── health.py
├── services/
│   ├── audit_log_service.py
│   └── health_service.py
└── main.py                    # App assembly: lifespan, middleware, handlers, routers
tests/
└── test_architecture.py       # Layer boundary checks
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
| `_find_one(filters)`, `_find_many(filters, limit, skip, sort)`, `_count(filters)`, `_exists(filters)` | protected | Building blocks for domain methods, used **only inside the repository** |

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
    async def update_one(self, id: str, data: Dict[str, Any]) -> bool: ...    # True if the document exists
    async def update_many(self, filters, data) -> int: ...                   # matched documents
    async def delete_one(self, id: str) -> bool: ...
    async def delete_many(self, filters: Dict[str, Any]) -> int: ...
```

- **`MongoStorage`** ([mongo_storage.py](app/db/mongo_storage.py)): PyMongo async API, documents stored as-is with `_id: ObjectId`. **Active backend.** The client is `tz_aware`, so datetimes come back as UTC-aware.
- **`PostgresStorage`** ([postgres_storage.py](app/db/postgres_storage.py)): **reference example, not wired in.** Each collection is a table `(id TEXT PRIMARY KEY, data JSONB)` created on first use. Numbers compare numerically, other values as text (datetimes in ISO format, all UTC). Table and field names must be plain identifiers.

Adding a backend = one new `{db}_storage.py` implementing `BaseStorage` + changes in `database.py`. Nothing else changes.

---

## Integrations

Connectors to external services live in `app/integrations`, grouped by capability (`llm/`, `payments/`, ...):

- `base_{capability}_client.py`: abstract interface (plain dicts in/out, no SDK types).
- `{provider}_client.py`: implementation. Wraps every provider failure in `ExternalServiceError`.
- [clients.py](app/integrations/clients.py): shared `httpx.AsyncClient` opened/closed in the app lifespan, plus one factory per capability (`get_llm_client()`). The factory is the only place that knows which provider is active.
- Configuration (API keys, base URLs, default models) goes in `Settings`.

Services use integrations through the factory:

```python
from app.integrations.clients import get_llm_client


class SummaryService:
    """Business logic for text summaries."""

    async def summarize(self, text: str) -> str:
        result = await get_llm_client().complete(
            [{"role": "user", "content": f"Summarize:\n{text}"}]
        )
        return result["content"]
```

The available LLM connector is `OpenRouterClient` (OpenAI-compatible API): set `OPENROUTER_API_KEY`, optionally `OPENROUTER_MODEL` (default `openrouter/auto`).

---

## Decorators

Every endpoint uses both decorators from [app/core/decorator.py](app/core/decorator.py), in this order (checked by the architecture test):

```python
@router.get("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(metadata={"service": "products"})
async def get_product(product_id: str) -> ProductResponse:
    ...
```

### @handle_errors

Converts exceptions raised by the endpoint into responses with body `{"error": "<ExceptionClass>", "message": "..."}`. Services raise exceptions from [app/core/exceptions.py](app/core/exceptions.py):

| Exception | Status |
|-----------|--------|
| `NotFoundError` | 404 |
| `InvalidInputError` | 400 |
| `ExternalServiceError` | 502 |
| Any other `AppError` | 400 |
| `HTTPException` | passed through unchanged |
| Unexpected exception | 500, generic message; traceback in the log, never in the response |
| Request validation (FastAPI) | 422 |

To add an error type: subclass `AppError` and add it to `_STATUS_CODES` in `decorator.py`.

### @audit_log

Records every call in the `audit_logs` collection: `action` (function name), `endpoint` (request path), `method`, `status` (`success`/`error`), `duration_ms`, `timestamp` (UTC), `metadata` (the dict passed to the decorator, plus `error` on failure).

Method and path are read from the request: the decorator adds a hidden `Request` parameter to the endpoint signature, so the endpoint must not declare one for it. A failure while writing the log is logged and never affects the response.

## Logging

`setup_logging()` ([logging_config.py](app/core/logging_config.py)) runs at startup and configures the `app` logger: stderr, format `timestamp LEVEL [logger.name] message`, level from `LOG_LEVEL`. Uvicorn and third-party loggers are left untouched.

In any module under `app/`:

```python
import logging

logger = logging.getLogger(__name__)
```

Never use `print`, and never log secrets (API keys, tokens, passwords, full LLM prompts with user data).

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

from app.core.decorator import audit_log, handle_errors
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
- **Mandatory decorators**: `@router.<method>` → `@handle_errors` → `@audit_log(metadata={"service": "<feature>"})` → `async def`.
- No try/except and no logic: the router only calls the service.

### 6. Register — `app/api/v1/__init__.py`

```python
from app.api.v1 import audit_log_router, health_router, product_router

api_router.include_router(product_router.router)
```

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

## Docker

`docker-compose.yaml` is for development: it mounts the code and runs uvicorn with `--reload`. The `Dockerfile` alone builds a self-contained image (code copied, non-root user, no reload).

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
- [ ] `app/api/v1/{feature}_router.py`: schemas only, `@handle_errors` + `@audit_log`, `response_model` + `status_code`
- [ ] Router registered in `app/api/v1/__init__.py`
- [ ] `pytest` passes

---

## Existing API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health/check` | API uptime and database reachability |
| GET | `/api/v1/audit-logs` | Audit logs in a date range, newest first |

`/audit-logs` query parameters: `start_date`, `end_date` (`YYYY-MM-DD`, inclusive, UTC), `limit` (1-1000, default 100), `skip` (default 0).

## License

MIT
