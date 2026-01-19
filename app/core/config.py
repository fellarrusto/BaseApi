from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Minerva Search"
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "sybilla_db"
    API_PORT: int = 9000
    MCP_PORT: int = 5009
    MCP_API_KEY: str = "dev-key"
    MCP_SERVER_URL: str = "http://localhost:8009"
    MONGO_VERSION: str = "6"
    MONGO_EXPRESS_PORT: int = 8081
    MONGO_EXPRESS_VERSION: str = "1.0.0-alpha.4"
    MONGO_EXPRESS_USER: str = "admin"
    MONGO_EXPRESS_PASSWORD: str = "admin"

    @property
    def MONGODB_URL(self):
        return self.MONGODB_URI
    
    @property
    def DATABASE_NAME(self):
        return self.MONGO_DB

    class Config:
        env_file = ".env"

settings = Settings()