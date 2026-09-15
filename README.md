# Base API

Modular FastAPI boilerplate for REST APIs, built on a strict layered architecture (Router → Service → Repository → Storage) with MongoDB as the default backend.

## Features

- **FastAPI** with full async support and auto-generated Swagger docs
- **Entity repositories** on top of a database-agnostic storage layer (MongoDB active, PostgreSQL provided as a reference example)
- **Integrations layer** for external services, with an OpenRouter LLM connector
- **Automatic audit logging** (middleware) and centralized error handling
- **Architecture tests** that enforce the layer boundaries
- **Docker-ready**: API, MongoDB and Mongo Express with a single command

## Quick Start

```bash
git clone <repo-url>
cd BaseApi
cp .env.example .env   # optional
docker-compose up -d
```

| Service | URL |
|---------|-----|
| REST API | http://localhost:5008/api/v1 |
| Swagger UI | http://localhost:5008/docs |
| Mongo Express | http://localhost:8081 (admin/admin) |

Run the architecture tests with `pip install -r requirements-dev.txt && pytest`.

## Documentation

Architecture, conventions, and the step-by-step guide for adding new features are in [CLAUDE.md](CLAUDE.md) — it also serves as the instruction file for AI coding agents.

## License

MIT
