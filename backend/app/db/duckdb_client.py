import duckdb
from app.config import settings

class DuckDBClient:
    @staticmethod
    def get_connection():
        # Open connection in read-only mode for safety and concurrency
        return duckdb.connect(database=settings.DATABASE_PATH, read_only=True)
