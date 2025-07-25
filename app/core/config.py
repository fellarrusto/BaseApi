from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SybillaApi"
    MONGODB_URL: str = "mongodb://mongo:27017"
    DATABASE_NAME: str = "sybilla_db"
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    
    # Task configuration
    PDF_INBOX_PATH: str = "./storage/pdf_inbox"

    class Config:
        env_file = ".env"

settings = Settings()