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
    Guarantees the connection is closed after execution completes.
    """
    conn = DuckDBClient.get_connection()
    try:
        yield conn
    finally:
        conn.close()
