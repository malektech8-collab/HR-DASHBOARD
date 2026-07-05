import duckdb
from app.config import settings
from typing import Generator

def configure_s3(conn):
    """Gracefully load S3 extensions and configure cloud credentials."""
    try:
        conn.execute("INSTALL httpfs;")
        conn.execute("LOAD httpfs;")
    except Exception as e:
        print(f"Warning: Could not install/load httpfs extension: {e}")
        
    try:
        conn.execute("INSTALL aws;")
        conn.execute("LOAD aws;")
        
        if settings.AWS_S3_ENDPOINT:
            conn.execute(f"""
                CREATE OR REPLACE SECRET (
                    TYPE S3,
                    KEY_ID '{settings.AWS_ACCESS_KEY_ID or ""}',
                    SECRET '{settings.AWS_SECRET_ACCESS_KEY or ""}',
                    REGION '{settings.AWS_DEFAULT_REGION or "us-east-1"}',
                    ENDPOINT '{settings.AWS_S3_ENDPOINT}',
                    USE_SSL {str(settings.AWS_S3_USE_SSL).upper()}
                );
            """)
        else:
            conn.execute("CALL load_aws_credentials();")
    except Exception as e:
        print(f"Warning: Could not configure AWS/S3 storage credentials: {e}")

class DuckDBClient:
    @staticmethod
    def get_connection():
        # Open connection in read-only mode for safety and concurrency
        conn = duckdb.connect(database=settings.DATABASE_PATH, read_only=True)
        configure_s3(conn)
        return conn


def get_db_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Dependency generator yielding a read-only DuckDB database connection.
    Sets thread limit to 1 to prevent CPU/thread contention under concurrent queries.
    """
    conn = DuckDBClient.get_connection()
    try:
        conn.execute("SET threads TO 1")
        yield conn
    finally:
        conn.close()
