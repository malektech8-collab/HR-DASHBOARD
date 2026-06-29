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
    
    # 1. Generate fake sample data
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
