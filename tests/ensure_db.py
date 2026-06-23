from pipeline.config import get_duckdb
with get_duckdb() as con:
    con.sql("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM prices").show()
    con.sql("SELECT COUNT(*) FROM prices WHERE volume IS NULL").show()
    con.sql("SELECT COUNT(*) FROM prices WHERE close <= 0 OR volume < 0").show()
    con.sql("SELECT ticker, COUNT(*) c FROM prices GROUP BY ticker ORDER BY c LIMIT 5").show()
