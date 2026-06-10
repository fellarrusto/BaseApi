# Base API - FastAPI Boilerplate

Modular template for REST APIs built with FastAPI on a strict layered architecture (Router → Service → Repository). MongoDB is the default storage backend; PostgreSQL is supported through the same repository interface.

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | ≥0.115.0 | Async web framework |
| MongoDB | 6 | Default NoSQL database |
| Motor | 3.3.2 | Async MongoDB driver |
| PostgreSQL | - | Alternative backend (reference example, asyncpg) |
| Pydantic | ≥2.5.0 | Data validation and settings |
| Docker | - | Containerization |

---

## Quick Start

```bash
# Clone and run
git clone <repo-url>
cd BaseApi
docker-compose up -d
```

**Available services:**
- REST API: `http://localhost:${API_PORT}/api/v1` (e.g. `5008`)
- Mongo Express: `http://localhost:8081` (admin/admin)
- Swagger UI: `http://localhost:${API_PORT}/docs`

---

## Architecture — MANDATORY Layered Pattern

**Every feature MUST follow the Model / Router / Service / Repository pattern. No exceptions.**

Request flow:

```
Router (HTTP) → Service (business logic) → Repository (data access) → Database
                     ↕
                Models (Pydantic DTOs)
```

Responsibilities — and hard boundaries:

| Layer | Does | NEVER does |
|-------|------|------------|
| **Model** | Defines Pydantic schemas (`InDB`, `Response`, `Create`, `Update`) | Business logic, DB access |
| **Router** | HTTP input/output validation, delegates to service | Business logic, DB access |
| **Service** | Business logic, Pydantic ↔ dict conversion | Direct driver access (Motor/asyncpg), HTTP parsing |
| **Repository** | Data access behind the `BaseRepository` interface | Business logic, HTTP concerns |

**Rules you must never break:**

1. A router never queries the database — it only calls its service.
2. A service never imports Motor, asyncpg, or `get_database()` — it only uses `BaseRepository` obtained via `get_repository()`.
3. Database-specific code lives **only** inside a repository implementation (`mongo_repository.py`, `postgres_repository.py`).
4. Models are pure data structures — no methods with business logic.
5. Skipping a layer (e.g. router → repository) is forbidden, even for "simple" endpoints.

This is what makes the storage backend swappable: services and routers are identical whether the app runs on MongoDB or PostgreSQL.

## Project Structure

```
app/
├── api/                       # HTTP routers (endpoints)
│   ├── __init__.py
│   ├── health_router.py
│   └── log_router.py
│
├── services/                  # Business logic layer
│   ├── __init__.py
│   ├── health_service.py
│   └── log_service.py
│
├── models/                    # Pydantic schemas
│   ├── __init__.py
│   ├── base.py                # PyObjectId validator
│   ├── health.py
│   ├── log.py
│   └── error.py
│
├── core/                      # Configuration and utilities
│   ├── __init__.py
│   ├── config.py              # Settings (env vars)
│   └── decorator.py           # @handle_errors, @audit_log
│
├── db/                        # Database layer (repository pattern)
│   ├── __init__.py
│   ├── database.py            # Connection lifecycle + get_repository() factory
│   ├── base_repository.py     # Abstract BaseRepository interface
│   ├── mongo_repository.py    # MongoDB implementation (Motor)
│   └── postgres_repository.py # PostgreSQL implementation (asyncpg, JSONB)
│
└── main.py                    # FastAPI entry point
```

---

## Repository Pattern

All data access goes through `BaseRepository` ([app/db/base_repository.py](app/db/base_repository.py)), a database-agnostic abstract interface. The factory `get_repository(collection)` in [app/db/database.py](app/db/database.py) returns the concrete implementation (currently `MongoRepository`).

**Interface:**

```python
class BaseRepository(ABC):
    async def find_one(self, id: str) -> Optional[Dict[str, Any]]: ...
    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    async def find_many(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None   # [("field", 1 | -1)]
    ) -> List[Dict[str, Any]]: ...
    async def count(self, filters: Dict[str, Any]) -> int: ...
    async def exists(self, filters: Dict[str, Any]) -> bool: ...
    async def insert_one(self, data: Dict[str, Any]) -> str: ...
    async def insert_many(self, data: List[Dict[str, Any]]) -> List[str]: ...
    async def update_one(self, id: str, data: Dict[str, Any]) -> bool: ...
    async def update_many(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int: ...
    async def delete_one(self, id: str) -> bool: ...
    async def delete_many(self, filters: Dict[str, Any]) -> int: ...
```

**Rules:**

1. Services depend **only** on `BaseRepository` — never on Motor, asyncpg, or `get_database()`.
2. Get a repository with `get_repository("collection_name")`.
3. Instantiate the repository **lazily** (the DB connection only exists after startup):

```python
class ProductService:
    def __init__(self):
        self._repo = None

    @property
    def repo(self) -> BaseRepository:
        if self._repo is None:
            self._repo = get_repository("products")
        return self._repo
```

4. Repositories work with plain `dict`s; Pydantic conversion happens in the service.
5. `find_one`/`update_one`/`delete_one` take the id as a string and handle id conversion internally (returning `None`/`False` for invalid ids).
6. Filters use Mongo-style syntax; both backends support equality plus `$gt`, `$gte`, `$lt`, `$lte`, `$ne`, `$in`.
7. Adding a new backend = one new file implementing `BaseRepository` + a branch in `get_repository()`. Nothing else changes.

### Implementations

- **`MongoRepository`** ([app/db/mongo_repository.py](app/db/mongo_repository.py)): native Motor implementation, documents stored as-is with `_id: ObjectId`. **This is the active backend.**
- **`PostgresRepository`** ([app/db/postgres_repository.py](app/db/postgres_repository.py)): **reference example, not wired into the app.** Document-style storage on PostgreSQL via asyncpg. Each collection maps to a table `(id TEXT PRIMARY KEY, data JSONB)` created automatically on first use. Filter values are compared as text, so range filters work on ISO-formatted dates.

---

## Switching to PostgreSQL

The codebase ships configured for MongoDB only. `PostgresRepository` is provided as a reference example: services and routers never change because they depend on `BaseRepository` only. To actually enable it:

### 1. Add the driver

**File:** `requirements.txt`

```
asyncpg>=0.29.0
```

### 2. Add the settings

**File:** `app/core/config.py` — these variables are intentionally NOT in `Settings` by default; add them only when switching:

```python
class Settings(BaseSettings):
    # ...existing settings...

    # PostgreSQL backend
    POSTGRES_URI: str = "postgresql://postgres:postgres@localhost:5432/base_api_db"
```

**File:** `.env`

```env
POSTGRES_URI=postgresql://postgres:postgres@base-postgres:5432/base_api_db
```

### 3. Wire connection and factory

**File:** `app/db/database.py` — open the pool at startup and return the Postgres repository:

```python
import asyncpg
from app.db.postgres_repository import PostgresRepository

async def db_connect():
    db.pg_pool = await asyncpg.create_pool(settings.POSTGRES_URI)

async def db_disconnect():
    if db.pg_pool:
        await db.pg_pool.close()

def get_repository(collection: str) -> BaseRepository:
    return PostgresRepository(db.pg_pool, collection)
```

### 4. Update docker-compose

**File:** `docker-compose.yaml` — add the PostgreSQL service and point `base-api` at it:

```yaml
services:
  base-api:
    # ...existing config...
    environment:
      - PYTHONUNBUFFERED=1
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

The `base-mongo` and `base-mongo-express` services can be removed when MongoDB is no longer needed.

### 5. Rebuild

```bash
docker-compose up -d --build
```

---

## Naming Conventions

### Files and Folders

| Type | Pattern | Example |
|------|---------|---------|
| Router | `{feature}_router.py` | `user_router.py` |
| Service | `{feature}_service.py` | `user_service.py` |
| Model | `{feature}.py` | `user.py` |
| Repository | `{db}_repository.py` | `mongo_repository.py` |

### Classes and Variables

| Type | Pattern | Example |
|------|---------|---------|
| DB model | `{Feature}InDB` | `UserInDB` |
| Response model | `{Feature}Response` | `UserResponse` |
| Create model | `{Feature}Create` | `UserCreate` |
| Update model | `{Feature}Update` | `UserUpdate` |
| Service class | `{Feature}Service` | `UserService` |
| Service instance | `{feature}_service` | `user_service` |
| Router instance | `router` | `router` |
| DB collection | `{features}` (plural, snake_case) | `users`, `audit_logs` |

### Python Code

- **Functions and variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Files**: `snake_case.py`

---

## Adding a New Feature

Follow these steps in order to add a new feature (example: `Product`). **All four layers are required.**

### 1. Create the Model

**File:** `app/models/product.py`

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.base import PyObjectId


class ProductInDB(BaseModel):
    """Persistence model."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: Optional[str] = None
    price: float
    category: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProductResponse(BaseModel):
    """API response model."""
    id: str
    name: str
    description: Optional[str]
    price: float
    category: str
    tags: List[str]
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProductCreate(BaseModel):
    """POST request model."""
    name: str
    description: Optional[str] = None
    price: float
    category: str
    tags: List[str] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """PUT/PATCH request model."""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
```

**Model rules:**

1. **Mandatory separation**: `InDB` for persistence, `Response` for API output, `Create`/`Update` for input
2. **MongoDB id**: always use `PyObjectId` with `alias="_id"`
3. **Timestamps**: `created_at` with `default_factory=datetime.utcnow`
4. **Type hints**: always complete; use `Optional[]` for nullable fields
5. **Config class**: always include `json_encoders` for datetime
6. **No logic**: models are pure data structures — no business methods

---

### 2. Create the Service

**File:** `app/services/product_service.py`

```python
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException

from app.db.base_repository import BaseRepository
from app.db.database import get_repository
from app.models.product import (
    ProductInDB,
    ProductResponse,
    ProductCreate,
    ProductUpdate
)


class ProductService:
    """Service handling product business logic."""

    def __init__(self):
        self._repo = None

    @property
    def repo(self) -> BaseRepository:
        if self._repo is None:
            self._repo = get_repository("products")
        return self._repo

    async def create(self, data: ProductCreate) -> ProductResponse:
        """Create a new product."""
        product = ProductInDB(**data.model_dump())
        product_id = await self.repo.insert_one(
            product.model_dump(by_alias=True)
        )

        created = await self.repo.find_one(product_id)
        return self._to_response(created)

    async def get_by_id(self, product_id: str) -> ProductResponse:
        """Fetch a product by id."""
        product = await self.repo.find_one(product_id)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return self._to_response(product)

    async def get_all(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[ProductResponse]:
        """Fetch all products with optional filters."""
        filters = {}
        if category:
            filters["category"] = category

        products = await self.repo.find_many(filters, limit=limit)
        return [self._to_response(p) for p in products]

    async def update(
        self,
        product_id: str,
        data: ProductUpdate
    ) -> ProductResponse:
        """Update an existing product."""
        update_data = {
            k: v for k, v in data.model_dump().items()
            if v is not None
        }
        update_data["updated_at"] = datetime.utcnow()

        updated = await self.repo.update_one(product_id, update_data)

        if not updated:
            raise HTTPException(status_code=404, detail="Product not found")

        return await self.get_by_id(product_id)

    async def delete(self, product_id: str) -> bool:
        """Delete a product."""
        deleted = await self.repo.delete_one(product_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Product not found")

        return True

    def _to_response(self, doc: dict) -> ProductResponse:
        """Convert a raw document into a ProductResponse."""
        return ProductResponse(
            id=str(doc["_id"]),
            name=doc["name"],
            description=doc.get("description"),
            price=doc["price"],
            category=doc["category"],
            tags=doc.get("tags", []),
            created_at=doc["created_at"]
        )


# Singleton instance
product_service = ProductService()
```

**Service rules:**

1. **One class per feature**: `ProductService` handles products only
2. **Singleton**: always export an instance `product_service = ProductService()`
3. **Lazy repository**: `repo` property calling `get_repository()` on first access
4. **Never use the driver directly**: every DB operation goes through the repository
5. **Async methods**: all DB operations must be async
6. **Typed returns**: always return Pydantic models (`Response` or `InDB`)
7. **HTTPException**: raise FastAPI exceptions for errors (404, 400, etc.)
8. **Private helper**: `_to_response()` for document → response conversion

---

### 3. Create the Router

**File:** `app/api/product_router.py`

```python
from typing import List, Optional
from fastapi import APIRouter, Query, status

from app.core.decorator import handle_errors, audit_log
from app.models.product import (
    ProductResponse,
    ProductCreate,
    ProductUpdate
)
from app.services.product_service import product_service


router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
@handle_errors
@audit_log(method="POST", metadata={"service": "products"})
async def create_product(data: ProductCreate) -> ProductResponse:
    """Create a new product."""
    return await product_service.create(data)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
@handle_errors
@audit_log(method="GET", metadata={"service": "products"})
async def get_product(product_id: str) -> ProductResponse:
    """Fetch a product by id."""
    return await product_service.get_by_id(product_id)


@router.get(
    "/",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK
)
@handle_errors
@audit_log(method="GET", metadata={"service": "products"})
async def get_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Max results")
) -> List[ProductResponse]:
    """Fetch all products with optional filters."""
    return await product_service.get_all(category=category, limit=limit)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
@handle_errors
@audit_log(method="PUT", metadata={"service": "products"})
async def update_product(
    product_id: str,
    data: ProductUpdate
) -> ProductResponse:
    """Update an existing product."""
    return await product_service.update(product_id, data)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@handle_errors
@audit_log(method="DELETE", metadata={"service": "products"})
async def delete_product(product_id: str) -> None:
    """Delete a product."""
    await product_service.delete(product_id)
```

**Router rules:**

1. **One router per feature**: separate file for each domain
2. **Prefix and tags**: always set `prefix="/feature"` and `tags=["feature"]`
3. **Mandatory decorators**: always apply `@handle_errors` and `@audit_log`
4. **Decorator order**: `@router.method` → `@handle_errors` → `@audit_log` → `async def`
5. **response_model**: always specify the response model
6. **Explicit status_code**: use `status.HTTP_*` for clarity
7. **Type hints**: return type always specified
8. **Docstring**: short description for every endpoint (shown in Swagger)
9. **Query params**: use `Query()` with description for documentation
10. **No logic**: the router only calls the service — zero business logic

---

### 4. Register the Router

**File:** `app/main.py`

Add the import and include the router:

```python
from app.api import health_router, log_router, product_router  # Added

# ...

router = APIRouter(prefix="/api/v1")
router.include_router(health_router.router)
router.include_router(log_router.router)
router.include_router(product_router.router)  # Added
```

---

## Available Decorators

### @handle_errors

Catches every exception and converts it into an `HTTPException` with traceback.

```python
@router.get("/")
@handle_errors
async def my_endpoint():
    # If anything fails, returns 500 with details
    ...
```

### @audit_log

Automatically records every call in the database (`audit_logs` collection).

```python
@router.get("/")
@handle_errors
@audit_log(method="GET", metadata={"service": "my_service"})
async def my_endpoint():
    ...
```

**Recorded fields:**
- `action`: function name
- `endpoint`: endpoint path
- `method`: HTTP method
- `status`: "success" or "error"
- `duration_ms`: execution time
- `metadata`: custom data
- `timestamp`: call date/time

---

## Configuration

### Environment Variables

**File:** `.env`

```env
# Ports
API_PORT=5008
MONGO_EXPRESS_PORT=8081

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGO_DB=base_api_db
MONGO_VERSION=6

# Mongo Express
MONGO_EXPRESS_VERSION=1.0.0-alpha.4
MONGO_EXPRESS_USER=admin
MONGO_EXPRESS_PASSWORD=admin
```

### Adding New Variables

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # Add new variables here
    MY_NEW_VAR: str = "default_value"
    MY_NEW_INT: int = 42

    class Config:
        env_file = ".env"
```

---

## Docker

### Useful Commands

```bash
# Start all services
docker-compose up -d

# Rebuild after changes
docker-compose up -d --build

# Logs
docker-compose logs -f base-api

# Stop
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Container Architecture (default, MongoDB backend)

```
┌─────────────────┐
│    base-api     │
│   (FastAPI)     │
│   port 5008     │
└────────┬────────┘
         │
  ┌──────┴──────┐
  │  base-mongo │
  │  (MongoDB)  │
  │ port 27017  │
  └──────┬──────┘
         │
┌────────┴──────────────┐
│   base-mongo-express  │
│    (Admin UI)         │
│     port 8081         │
└───────────────────────┘
```

See [Switching to PostgreSQL](#switching-to-postgresql) for the PostgreSQL setup.

---

## Code Style

### Imports

Mandatory order:

```python
# 1. Standard library
from datetime import datetime
from typing import List, Optional
import time

# 2. Third-party
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from bson import ObjectId

# 3. Local imports
from app.core.config import settings
from app.db.database import get_repository
from app.models.product import ProductResponse
```

### Type Hints

Always complete:

```python
# ✅ Correct
async def get_products(limit: int = 100) -> List[ProductResponse]:
    ...

# ❌ Wrong
async def get_products(limit=100):
    ...
```

### Docstrings

Google style for public functions:

```python
async def create_product(data: ProductCreate) -> ProductResponse:
    """
    Create a new product in the database.

    Args:
        data: Product data to create

    Returns:
        The created product with assigned id

    Raises:
        HTTPException: If validation fails
    """
    ...
```

### Async/Await

All I/O operations must be async:

```python
# ✅ Correct
async def get_product(product_id: str) -> Optional[dict]:
    return await self.repo.find_one(product_id)

# ❌ Wrong (blocks the event loop)
def get_product(product_id: str) -> Optional[dict]:
    return self.repo.find_one(product_id)
```

---

## New Feature Checklist

- [ ] Model created in `app/models/{feature}.py`
  - [ ] `{Feature}InDB` with `PyObjectId` and `alias="_id"`
  - [ ] `{Feature}Response` for API output
  - [ ] `{Feature}Create` for POST input
  - [ ] `{Feature}Update` for PUT/PATCH input (optional)
- [ ] Service created in `app/services/{feature}_service.py`
  - [ ] `{Feature}Service` class
  - [ ] Lazy `repo` property using `get_repository("collection")`
  - [ ] Async CRUD methods using the repository only
  - [ ] Singleton instance exported
- [ ] Router created in `app/api/{feature}_router.py`
  - [ ] `prefix` and `tags` configured
  - [ ] `@handle_errors` and `@audit_log` decorators applied
  - [ ] `response_model` and `status_code` specified
- [ ] Router registered in `app/main.py`
- [ ] No layer skipped, no direct driver access anywhere

---

## Existing API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health/check` | API health check |
| GET | `/api/v1/logs/audit` | Fetch audit logs by date range |

**`/logs/audit` parameters:**
- `start_date`: start date (format: DD-MM-YYYY)
- `end_date`: end date (format: DD-MM-YYYY)

---

## Troubleshooting

### MongoDB Connection Error

```bash
# Check that MongoDB is running
docker-compose ps base-mongo

# Check the logs
docker-compose logs base-mongo
```

### Import Error

Check that `PYTHONPATH` is configured:

```bash
# Inside the container
export PYTHONPATH=/app
```

---

## License

MIT
