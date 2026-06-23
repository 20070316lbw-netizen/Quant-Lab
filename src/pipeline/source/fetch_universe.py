"""标的池(universe)数据源: 从 Wikipedia 抓取 S&P 500 成分股列表"""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests
from loguru import logger

from pipeline.base import DataSource

_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

class SP500Universe(DataSource):
    """S&P 500 成分股列表。

    Returns 列:
        ticker   (str): 股票代码, 已规范化('.' -> '-' 以兼容 yfinance, 如 BRK.B -> BRK-B)。
        security (str): 公司名称。
        cik      (str): SEC 的 10 位零填充 CIK, 基本面抓取要用它定位公司。
    """

    def fetch(self) -> pd.DataFrame:
        logger.info("正在抓取 S&P 500 成分股列表 ...")
        resp = requests.get(_WIKI_URL, headers = {"User-Agent": _BROWSER_UA}, timeout = 30)
        resp.raise_for_status()

        table = pd.read_html(StringIO(resp.text))[0]

        df = table.rename(
            columns = {"Symbol" : "ticker",
                       "Security" : "security",
                       "CIK" : "cik"}
        )[["ticker", "security", "cik"]].copy()

        # 规范化: CIK 左补零到 10 位(EDGAR 接口只吃 10 位)
        df["cik"] = df["cik"].astype("Int64").astype(str).str.zfill(10)
        df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)

        return df
    
        

if __name__ == "__main__":
    S = SP500Universe()
    df = S.fetch()
    print(df)


