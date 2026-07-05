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

    # S3 / Cloud Storage configurations
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_DEFAULT_REGION: str | None = None
    AWS_S3_ENDPOINT: str | None = None
    AWS_S3_USE_SSL: bool = True
    DATA_PREFIX: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

