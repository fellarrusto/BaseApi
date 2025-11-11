import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Minerva Search"
    MONGODB_URL: str = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.environ.get("MONGO_DB", "sybilla_db")

    class Config:
        env_file = ".env"

settings = Settings()