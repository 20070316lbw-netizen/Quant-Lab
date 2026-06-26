"""价量数据源: 用 yfinance 抓取单只股票日频 OHLCV"""

from __future__ import annotations

import pandas as pd 
import yfinance as yf

from loguru import logger

from pipeline.base import DataSource
from pipeline.error import YahooFetchError

# 入库顺序定义: fetch() 严格产出这个顺序, 后续直接对应 SELECT * 建表
OHLCV_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume"]

class YahooPrices(DataSource):
    """单只股票日频价量
    
    args:
        ticker: 股票代码
        period: 周期字符串
        
    returns 列: data, ticker, open, high, low, close, volume
    """

    def __init__(self, ticker: str, period: str = "1y") -> None:
        self.ticker = ticker
        self.period = period


    def fetch(self) -> pd.DataFrame:
        logger.info(f"正在抓取 {self.ticker} 价量 (period = {self.period})")

        # auto_adjust=False: 保留原始 OHLC, 复权与否由后续因子层自己决定, 数据层不替它做主。
        # TODO: yfinance 网络请求缺少显式超时/重试控制，后续可封装统一下载函数避免偶发卡死或失败
        raw = yf.Ticker(self.ticker).history(self.period, auto_adjust = False)

        # TODO: 空数据之外还应捕获 yfinance 网络异常/限流异常，并统一转成 YahooFetchError
        if raw.empty:
            raise YahooFetchError(f"{self.ticker} 未返回任何价量数据")
        
        df = raw.reset_index().rename(
            columns={
                "Date" : "date",
                "Open" : "open",
                "High" : "high",
                "Low" : "low",
                "Close" : "close",
                "Volume" : "volume"
            }
        )
        
        df["ticker"] = self.ticker

        # TODO: 这里会把 datetime64 转成 Python date object，后续入库/回测前需确认是否统一使用 datetime64[ns]
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # TODO: 这里假设 yfinance 一定返回所有 OHLCV 字段，后续应在选列前做 schema 校验并给出清晰报错
        df = df[OHLCV_COLUMNS]

        # TODO: 当前 f-string 内外都使用双引号会导致语法错误，需改成 df['date'].max() 或调整外层引号
        logger.success(
            f"{self.ticker}: {len(df)} 行, {df['date'].min()} ~ {df["date"].max()}"
        )

        return df



if __name__ == "__main__":
    from pipeline.config import TEMP_DIR
    TEMP_DIR.parent.mkdir(parents=True, exist_ok=True)
    Y = YahooPrices("AAPL")
    raw = Y.fetch()
    # TODO: TEMP_DIR 名字像目录但这里当成 csv 文件路径使用，建议确认 config 里它到底是文件还是目录
    raw.to_csv(TEMP_DIR, index = False,encoding = "utf-8")
    logger.info("写入成功")

        
