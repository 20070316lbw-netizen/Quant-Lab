from pipeline.config import get_duckdb
with get_duckdb() as con:
    print(con.execute("SELECT ticker, count(*), min(date), max(date) FROM prices GROUP BY ticker").fetchall())