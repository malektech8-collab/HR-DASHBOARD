import duckdb
from app.config import settings
from typing import Generator

class DuckDBClient:
    @staticmethod
    def get_connection():
        # Open connection in read-only mode for safety and concurrency
        return duckdb.connect(database=settings.DATABASE_PATH, read_only=True)

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
