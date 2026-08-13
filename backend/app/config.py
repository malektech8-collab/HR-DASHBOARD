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

    # The reporting period the whole system reports on, when the operator sets
    # it explicitly. Honoured in BOTH modes and it OVERRIDES derivation from the
    # data — a reporting period is an operator decision, not a data artefact.
    # Unset (None) means "derive it". Format: YYYY-MM.
    REPORT_MONTH: str | None = None

    # DEMO ONLY. The sample-data report month, mirroring dbt_project.yml's
    # `report_month` default.
    #
    # This was the system-wide fallback until Phase 2 P0-3 (2a.5). It is no
    # longer reachable in real mode, and that is the point: with payroll and
    # compliance both absent, derivation used to land here, so a client
    # onboarding employees-only got every date window silently anchored to a
    # constant in this repo. Before anchor convergence that produced a NULL
    # anchor and a zero that LOOKED wrong; after it, a stale-but-plausible
    # number that looks RIGHT. Real mode now aborts and names REPORT_MONTH
    # instead. See scripts/report_period.py.
    DEFAULT_REPORT_MONTH: str = "2026-06"

    # The JWT signing key for THIS deployment. No default, deliberately.
    #
    # This replaced a committed module constant that was identical in every
    # deployment of the product, so a forged SYSTEM_ADMIN token needed only
    # repository access - not server access - and worked at every customer
    # install. Real mode now refuses to start without a per-deployment value;
    # demo generates a random one per process. See app/core/security.py.
    #
    # Generate:  python -c "import secrets; print(secrets.token_urlsafe(64))"
    JWT_SECRET: str | None = None

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

        # EXPLICIT, and it is the strict option on purpose.
        #
        # pydantic-settings defaults to "forbid" already; stating it makes the
        # choice deliberate rather than inherited, because the alternative was
        # considered and rejected.
        #
        # The alternative was "ignore", the one-character fix for a real
        # defect: .env.example shipped VITE_API_URL, so copying it to .env -
        # the documented first step - made this class raise at import and the
        # backend could not start.
        #
        # "forbid" was kept because it catches a variable that does not belong
        # in this file AT ALL, which is exactly the defect that occurred. The
        # right fix was to move the frontend variable to frontend/.env.example,
        # where Vite actually reads it; it was never read here, so its only
        # effect was the crash.
        #
        # MEASURED LIMITATION, so nobody relies on this for more than it does:
        # "forbid" does NOT catch a typo that PREFIXES an existing field name.
        # pydantic-settings matches those against the field and discards the
        # remainder silently, so both of these are ACCEPTED and ignored:
        #
        #     DATA_MODEE=real      -> DATA_MODE keeps its default, no error
        #     JWT_SECRETT=abc      -> JWT_SECRET stays unset, no error
        #
        # whereas VITE_API_URL and TOTALLY_UNRELATED are refused. So this
        # setting protects against misplaced variables, not against misspelled
        # ones. Real mode's own fail-closed checks are what catch the second
        # kind: an unset JWT_SECRET refuses to start (app/core/security.py).
        extra = "forbid"


settings = Settings()

