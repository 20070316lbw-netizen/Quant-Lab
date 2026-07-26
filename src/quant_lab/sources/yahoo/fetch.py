"""Yahoo 数据源抓取 OHLCV 等数据,其中收盘价分 close 和 adj_close。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf
from loguru import logger

from quant_lab.config import SP500_CACHE_PATH
from quant_lab.connection import get_pgsql
from quant_lab.error import YahooFetchError
from quant_lab.sources.base import DataSource

# 两张价格表使用各自独立的字段顺序:
# 原始表保留 Yahoo 返回的 adj_close 和公司行动,复权表只保存复权后的 OHLCV。
RAW_PRICE_COLUMNS = [
    "trade_date", "ticker", "open", "high", "low", "close",
    "adj_close", "volume", "dividends", "stock_splits",
]
ADJ_PRICE_COLUMNS = ["trade_date", "ticker", "open", "high", "low", "close", "volume"]


# sp500 缓存文件路径转化成真实路径
cache_path = Path(SP500_CACHE_PATH)


class Yahoo(DataSource):
    """单只股票日频价量数据源。

    单个实例只负责一只 ticker; 批量抓整个 universe 由模块级的
    fetch_sp500_prices() 编排, 不在这个类里做（对应"单 ticker,
    批量放外层"）。
    """
    

    def __init__(self, *, ticker: str, period: str = "10y"):
        self.ticker = ticker
        self.period = period


    def fetch(self, *, adjusted: bool) -> pd.DataFrame:
        """抓取 self.ticker 的日频价量。

        Args:
            adjusted:
                False -> 未复权 OHLC + adj_close + 分红/拆股 (RAW_PRICE_COLUMNS)
                True  -> 已复权 OHLCV, 全部价格字段都是复权后的值 (ADJ_PRICE_COLUMNS)

        决策: 不给默认值。两份数据字段结构不一样, 强制每次显式传,
        避免手滑漏传导致存错表(跟 pipeline/universe.py 里 target: DBTarget
        不设默认值是同一个理由)。
        """
        return self._get_adj_prices() if adjusted else self._get_prices()


    def _get_prices(self) -> pd.DataFrame:
        # auto_adjust=False
        # 返回原始 OHLC、Adj Close、Volume 和公司行动

        raw = yf.Ticker(self.ticker).history(self.period, auto_adjust = False)

        if raw.empty:
            raise YahooFetchError(f"{self.ticker} 未返回任何价量数据")

        df = raw.reset_index().rename(
            columns={
                "Date": "trade_date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
                "Dividends": "dividends",
                "Stock Splits": "stock_splits",
            }
        )

        df["ticker"] = self.ticker
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

        df = df[RAW_PRICE_COLUMNS]

        logger.success(
            f"{self.ticker} [未复权]: {len(df)} 行, "
            f"{df['trade_date'].min()} ~ {df['trade_date'].max()}"
        )

        return df


    def _get_adj_prices(self) -> pd.DataFrame:
        # auto_adjust=True: OHLC 全部按拆股/分红回溯调整, 用于算收益率。
        # 跟 _get_prices() 是两次独立请求 —— auto_adjust=False 时只有
        # Close 有对应的调整值(Adj Close), Open/High/Low 仍是原始值,
        # 不能只发一次请求就把两份数据都凑出来。

        
        raw = yf.Ticker(self.ticker).history(self.period, auto_adjust = True)

        if raw.empty:
            raise YahooFetchError(f"{self.ticker} 未返回任何价量数据")

        df = raw.reset_index().rename(
            columns={
                "Date": "trade_date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        df["ticker"] = self.ticker
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

        df = df[ADJ_PRICE_COLUMNS]

        logger.success(
            f"{self.ticker} [已复权]: {len(df)} 行, "
            f"{df['trade_date'].min()} ~ {df['trade_date'].max()}"
        )

        return df

    

def _load_sp500_dateframe() -> pd.DataFrame:
    """检查 sp500 缓存 csv文件是否存在, 如果存在则直接读取, 如果不存在则读取 pgsql 数据库内容并返回内容"""

    if cache_path.exists():
        return pd.read_csv(cache_path, dtype = {"cik": str})

    with get_pgsql(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT ticker, company_name, cik FROM universe.sp500_universe"
        )

        rows = cur.fetchall()
        # cur.execute(...) 只是发送并执行这条 SQL,并不会把结果直接给你。
        # 执行完之后,结果集停留在数据库连接的"缓冲区"里,你要主动用几种方法之一去取:
        # cur.fetchall() —— 一次性把所有结果行取出来,返回一个 list(每个元素是一行,通常是 tuple)
        # cur.fetchone() —— 一次只取一行
        # cur.fetchmany(n) —— 一次取 n 行

        assert cur.description is not None
        # psycopg3 给 cursor.description 的类型标注是 list[Column] | None。
        # 文档里也写了"如果上一次执行的语句不返回结果集(比如 INSERT/UPDATE,或者还没执行过任何语句),
        # 这个属性就是 None"。Pylance 只看类型签名,它不知道你这里执行的是 SELECT、一定会有结果集,
        # 所以只要你对 cur.description 做 for desc in cur.description 这种迭代,
        # 它就会警告"这玩意儿类型上可能是 None,不能迭代"。
        # assert 是 Python 的断言语句,格式是 `assert 条件, 可选的错误信息`。执行到这一行时:
        # 如果"条件"为真,什么都不发生,继续往下执行
        # 如果"条件"为假,直接抛出 AssertionError,程序中断
        # 放在这里的作用有两个:
        # 给 Pylance 看:类型检查器看到这行,就知道"经过这行代码之后
        # cur.description 的类型被收窄为非 None 了",后面再用就不报警告            # 给运行时看:万一真出现异常情况(比如 SQL 写错导致没有结果集),
        # 会在这里就报错,而不是拖到后面某处出现更莫名其妙的报错

        columns = [desc[0] for desc in cur.description]
        # cur.description——psycopg 的 cursor 执行完 SELECT 后,
        # description 里带着结果集的列名,
        # 用它拼 DataFrame 的列名比手写 ["ticker", "company_name", "cik"] 
        # 更不容易在 SQL 改列时忘记同步

    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(cache_path, index=False)          # 加 `index = Fales` 让写出的内容是干净的

    return df

def fetch_sp500_prices(*, adjusted: bool) -> pd.DataFrame:
    """遍历整个 sp500 universe, 对每只 ticker 调 Yahoo.fetch(), 合并成一张大表。

    单只 ticker 抓取失败时记录警告并跳过, 不中断整批。

    决策: 如果 500 只全部失败, 直接 raise 而不是默默返回空 DataFrame ——
    照你 universe 那边的思路(EmptyUniverseError), 全军覆没大概率是网络/
    limit 之类的系统性问题, 不该被当成"这批数据就是没有"悄悄放过。
    这一条你多半会反对, 帮忙重点看一下。

    TODO: 目前是顺序循环, 500 只票请求量不小, 后续要考虑并发/限流,
    以及给 yfinance 请求加超时重试(继承自旧代码里就有的 TODO)
    """

    targets = _load_sp500_dateframe()["ticker"]

    frames: list[pd.DataFrame] = []

    for t in targets:
        try:
            # 左边的 adjusted：是 fetch() 的参数名，来自 Yahoo.fetch(self, *, adjusted: bool)那个签名
            # 固定写死的，因为函数签名就叫这个名字。
            # 右边的 adjusted：是 fetch_sp500_prices(*, adjusted: bool) 
            # 这个函数自己的局部变量，装的是调用者传进来的那个 True/False 值。
            frames.append(Yahoo(ticker=t).fetch(adjusted=adjusted))

        except YahooFetchError as exc:
            logger.warning(f"{t} 抓取失败, 跳过: {exc}")

    if not frames:
        raise YahooFetchError(f"整批抓取失败, 共尝试抓取 {len(targets)} 只, 无一成功")

    kind = "已复权" if adjusted else "未复权"

    logger.success(
        f"sp500 [{kind}] 抓取完成, 共 {len(targets)} 只, 成功 {len(frames)} 只"
    )

    return pd.concat(frames, ignore_index=True)
    # ignore_index=True：这个是关键，不加会出问题。
    # 原因是：_get_prices()/_get_adj_prices() 里都调用了 raw.reset_index()，
    # 这一步会把每只票各自的行号重新编成 0, 1, 2, 3, ...。举个例子：
    # AAPL 那份 df：index 是 0, 1, 2, ..., 2515（10年大约2500多个交易日）
    # MSFT 那份 df：index 也是 0, 1, 2, ..., 2515
    # 如果直接 pd.concat(frames)（不加 ignore_index=True），
    # 拼出来的大表里，index 会是
    #  0,1,2,...,2515,  0,1,2,...,2515,  0,1,2,...
    # ——每只票都从 0 开始重复一遍，整张表里有几百组重复的 index。
    # 这会导致后续任何用 .loc[0] 这种按 index 取行的操作，
    # 一次性抓出几百只票"各自的第 0 行"而不是一行，很容易出隐蔽 bug。
    # 加上 ignore_index=True 之后，pd.concat 会丢掉每个子表原来的 index，
    # 重新生成一份从 0 到 N-1 连续不重复的新 index（N 是拼完之后的总行数，
    # 比如 500 只票 × 2500 行 ≈ 125万行，新 index 就是 0, 1, 2, ..., 1249999）。
    # 这个新 index 本身没有业务含义（不代表日期也不代表哪只票），
    # 纯粹保证唯一性——反正你们真正定位一行数据靠的是 trade_date + ticker 这两列
    # 跟 db/schema/0002_prices.sql 里 PRIMARY KEY (date, ticker) 是一个思路），
    # 不靠这个自动生成的行号。
            





    



    
