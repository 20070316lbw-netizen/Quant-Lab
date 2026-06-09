import duckdb
from pathlib import Path
from loguru import logger
PROJECT_ROOT = Path(__file__).resolve().parent

DATABASE_PATH = PROJECT_ROOT / "data.duckdb"
SP500_CACHE_PATH = PROJECT_ROOT / "database" / "sp500_ticker.csv"



def get_duckdb() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database = str(DATABASE_PATH))