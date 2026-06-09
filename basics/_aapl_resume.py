import duckdb
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_duckdb

def _get_aapl_resume_log(con: duckdb.DuckDBPyConnection) -> float:
    with get_duckdb() as con:
        df = con.execute("""
                         SELECT close, date FROM prices
                         
                         """).fetchdf()
        

    return 0.1