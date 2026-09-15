from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Base API"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"

    # Browser origins allowed to call the API, as a JSON list. Empty = CORS disabled
    CORS_ORIGINS: List[str] = []

    # Accept "mock:<user_id>:<role1>,<role2>" bearer tokens. Local testing only
    AUTH_MOCK_ENABLED: bool = False

    # Background jobs worker (python -m app.worker)
    WORKER_CONCURRENCY: int = 4          # jobs running at the same time per worker
    WORKER_POLL_SECONDS: float = 2.0     # wait between checks when the queue is empty
    WORKER_LOCK_SECONDS: float = 60.0    # a job whose worker is silent this long is retried

    # Retention in days (0 = keep forever). Changing it requires dropping the TTL index
    AUDIT_LOG_RETENTION_DAYS: int = 90
    JOB_RETENTION_DAYS: int = 30         # counted from the job end

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "base_api_db"

    # External integrations
    HTTP_TIMEOUT_SECONDS: float = 30.0


settings = Settings()
