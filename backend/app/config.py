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

    # Data mode: 'demo' (committed default) serves synthetic sample data;
    # 'real' is set locally (uncommitted, via .env / env var) for real-data use.
    DATA_MODE: str = "demo"

    # The ONE hardcoded report-month fallback for the whole system (cycle 5a).
    # Mirrors the dbt_project.yml `report_month` default. Both the pipeline
    # (build_warehouse.py) derivation fallback and the API resolver's no-row/
    # error fallback read THIS value, so they can never drift apart.
    DEFAULT_REPORT_MONTH: str = "2026-06"

    # S3 / Cloud Storage configurations
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_DEFAULT_REGION: str | None = None
    AWS_S3_ENDPOINT: str | None = None
    AWS_S3_USE_SSL: bool = True
    DATA_PREFIX: str = ""

    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"

    class Config:
        env_file = ".env"


settings = Settings()

