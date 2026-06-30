"""标的池(universe)数据源: 从 Wikipedia 抓取 S&P 500 成分股列表"""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests
from loguru import logger

from quant_lab.sources.base import DataSource

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
        # TODO: 增加 requests.RequestException 捕获并统一转换为项目内部异常类型
        resp = requests.get(_WIKI_URL, headers = {"User-Agent": _BROWSER_UA}, timeout = 30)
        resp.raise_for_status()

        # TODO: Wikipedia 页面结构变更后 [0] 可能不再是成分股表，建议增加表结构校验
        table = pd.read_html(StringIO(resp.text))[0]

        # TODO: 当前假设 Symbol/Security/CIK 三列始终存在，后续应校验列名后再重命名
        df = table.rename(
            columns = {"Symbol" : "ticker",
                       "Security" : "security",
                       "CIK" : "cik"}
        )[["ticker", "security", "cik"]].copy()

        # 规范化: CIK 左补零到 10 位(EDGAR 接口只吃 10 位)
        # TODO: 若 Wikipedia 出现缺失值，astype(str) 可能产生 '<NA>' 字符串，需要单独处理
        df["cik"] = df["cik"].astype("Int64").astype(str).str.zfill(10)
        df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)

        # TODO: 考虑记录抓取数量和样本范围，便于后续排查 universe 变化
        return df
    
        

if __name__ == "__main__":
    S = SP500Universe()
    df = S.fetch()
    # TODO: 调试代码，后续改成 logger 或单元测试
    print(df)


