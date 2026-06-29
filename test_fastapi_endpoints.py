import sys
sys.path.append("backend")
import duckdb
from app.config import settings
from app.db.duckdb_client import DuckDBClient

print("settings.DATABASE_PATH:", settings.DATABASE_PATH)
try:
    conn = DuckDBClient.get_connection()
    print("Database opened successfully.")
    
    print("Querying mart_command_center_overview...")
    rows = conn.execute("SELECT * FROM mart_command_center_overview").fetchall()
    print("  Success! Row count:", len(rows))
    conn.close()
except Exception as e:
    import traceback
    traceback.print_exc()
