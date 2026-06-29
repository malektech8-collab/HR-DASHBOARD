import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH", 
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "warehouse", "hr_analytics.duckdb"))
    )
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()

