import os
import sys

# Ensure current directory is on python path to enable imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from generate_sample_data import create_sample_data
from ingest_raw import ingest
from validate_data import validate
from build_warehouse import build_warehouse

def main():
    print("=========================================")
    print("STARTING FULL HR DATA PIPELINE REFRESH")
    print("=========================================")
    
    # 1. Generate fake sample data - DEMO ONLY.
    #
    # In real mode this must not run: it writes data/sample/*.csv, and P0-1
    # made real mode fail closed precisely so a contracted domain can never be
    # served from sample. Regenerating sample during a real run is harmless
    # today only because nothing reads it; leaving it unconditional is how that
    # stops being true.
    if os.getenv("DATA_MODE", "demo") == "real":
        print("Real mode: skipping sample generation.")
    else:
        create_sample_data()
    
    # 2. Ingest CSVs to Parquet (bronze & silver)
    ingest()
    
    # 3. Validate silver Parquet files and write gold DQ report
    validate()
    
    # 4. Build DuckDB warehouse tables and views
    build_warehouse()
    
    print("=========================================")
    print("HR DATA PIPELINE REFRESH COMPLETE")
    print("=========================================")

if __name__ == "__main__":
    main()
