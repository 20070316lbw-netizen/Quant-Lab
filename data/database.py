import sys
import yfinance as yf
import duckdb
import pandas as pd
from loguru import logger
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATABASE_PATH, get_duckdb
from fetch_stock import _fetch_stock


def _create_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
                CREATE TABLE IF NOT EXISTS 
                prices(
                    date                   DATE,
                    ticker                 VARCHAR,
                    open                   DOUBLE,   
                    high                   DOUBLE,
                    low                    DOUBLE,
                    close                  DOUBLE,
                    volume                 BIGINT,
                PRIMARY KEY (date, ticker)
                )""")
    logger.info(f"已执行 _crete_table() 方法")

def insert_prices(con: duckdb.DuckDBPyConnection,
                  df: pd.DataFrame,
                  ticker: str,
                  ) -> None:
    df["ticker"] = ticker
    df = df.reset_index()
    df = df.drop(columns = ["Dividends", "Stock Splits"] )
    df = df[["Date",
             "ticker", 
             "Open", 
             "High", 
             "Low", 
             "Close", 
             "Volume",
             ]]
    
    con.execute("""
                INSERT OR REPLACE INTO prices 
                SELECT * FROM df
                """)
    
def get_last_date(con: duckdb.DuckDBPyConnection,
                  ticker: str) -> date | None:
    try:
        db_date = con.execute("""
                            SELECT MAX(date) FROM prices
                            WHERE TICKER = ?
                            """,
                              [ticker]
                              ).fetchone()
        if db_date is None:
            return None
        logger.info(f"成功取到数据库内最新日期 {db_date[0]}")
        return db_date[0]
    except Exception as e:
        logger.error(f"无法得到最新日期, -{e}")
        return None
    
    


if __name__ == "__main__":
    df = _fetch_stock()
    with get_duckdb() as con:
        _create_table(con)
        insert_prices(con, df, ticker = "AAPL")
        df_db = con.execute("""
                            SELECT * FROM prices
                            LIMIT 5
                            """).fetchdf()
        print(df_db)
        print(get_last_date(con, ticker = "AAPL"))
        


