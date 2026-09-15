from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Base API"
    APP_VERSION: str = "1.0.0"

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "base_api_db"

    # External integrations
    HTTP_TIMEOUT_SECONDS: float = 30.0
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openrouter/auto"


settings = Settings()
