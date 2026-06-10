from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Base API"
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "sybilla_db"
    MONGO_VERSION: str = "6"
    MONGO_EXPRESS_PORT: int = 8081
    MONGO_EXPRESS_VERSION: str = "1.0.0-alpha.4"
    MONGO_EXPRESS_USER: str = "admin"
    MONGO_EXPRESS_PASSWORD: str = "admin"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
