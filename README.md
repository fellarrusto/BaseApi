# Base API - FastAPI MongoDB Template

Minimal FastAPI + MongoDB starter with modular pattern for scalable projects.

## Stack
- FastAPI
- MongoDB (Motor async)
- Pydantic v2
- Docker Compose

## Setup
```bash
docker-compose up -d
```

API: http://localhost:9000
Mongo Express: http://localhost:8081 (admin/admin)

## Structure
```
app/
├── api/              # Route endpoints
├── services/         # Business logic
├── models/           # Pydantic models
├── core/             # Config, decorators
└── db/               # Database connection
```

## Pattern

Each feature follows:
1. **Model** (`models/`) - Data schema (InDB + Response)
2. **Service** (`services/`) - Business logic
3. **Router** (`api/`) - HTTP endpoints

### Decorators

- `@handle_errors` - Error handling
- `@audit_log` - Automatic call logging

## Endpoints
```bash
GET /api/v1/health/check
GET /api/v1/logs/audit?start_date=01-01-2025&end_date=31-01-2025
```

## Adding a Feature
```python
# models/resource.py
class ResourceInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str

# services/resource_service.py
class ResourceService:
    async def create(self, data): ...

# api/resource_router.py
@router.post("/")
@handle_errors
@audit_log(method="POST")
async def create(data: ResourceCreate):
    return await resource_service.create(data)
```

## Environment Variables
```env
MONGODB_URI=mongodb://localhost:27017
MONGO_DB=sybilla_db
```