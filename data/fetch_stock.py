import sys
import yfinance as yf
import duckdb
import pandas as pd
from loguru import logger
from pathlib import Path

def _fetch_stock(ticker: str = "AAPL",
                period: str = "1y",
                ) -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker).history(period)
        if len(df) != 0:
            logger.info(f"成功抓取 {ticker} 股票数据, 时间 {period}")
            return df
        else:
            logger.error(f"抓取数据为空")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"抓取失败 {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    df = _fetch_stock()
    print(df)
    
    