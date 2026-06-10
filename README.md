# Base API

Modular FastAPI boilerplate for REST APIs, built on a strict layered architecture (Router → Service → Repository) with MongoDB as the default backend.

## Features

- **FastAPI** with full async support and auto-generated Swagger docs
- **Repository pattern**: database-agnostic data access (`MongoRepository` included, `PostgresRepository` provided as a reference example)
- **Audit logging** and centralized error handling via decorators
- **Docker-ready**: API, MongoDB and Mongo Express with a single command

## Quick Start

```bash
git clone <repo-url>
cd BaseApi
docker-compose up -d
```

| Service | URL |
|---------|-----|
| REST API | http://localhost:5008/api/v1 |
| Swagger UI | http://localhost:5008/docs |
| Mongo Express | http://localhost:8081 (admin/admin) |

Ports and credentials can be customized via a `.env` file (sensible defaults are provided).

## Documentation

Architecture, conventions, and the step-by-step guide for adding new features are in [CLAUDE.md](CLAUDE.md) — it also serves as the instruction file for AI coding agents.

## License

MIT
