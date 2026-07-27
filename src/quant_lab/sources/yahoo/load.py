"""S&P 500 全体股票抓取入库

数据库: PostgreSQL
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import psycopg
from loguru import logger
from psycopg import sql

from quant_lab.config import SCHEMA_OLCHV, SCHEMA_OLCHV_ADJ
from quant_lab.connection import get_pgsql
from quant_lab.error import YahooLo
from quant_lab.sources.yahoo.columns import (
    ADJ_PRICE_COLUMNS,
    RAW_PRICE_COLUMNS,
)


@dataclass(frozen=True)    # 对象的字段不能变, 但是字段比如是 list 那内部还是可以 append()
class _PriceTableSpec:
    """一类价格 DataFrame 对应的数据库写入契约。"""

    schema  : str
    table   : str
    columns : tuple[str, ...]

_PRICE_TABLE_SPECS: dict[bool, _PriceTableSpec] = {
    False: _PriceTableSpec(
        schema="market_data",
        table="daily_prices",
        columns=RAW_PRICE_COLUMNS,
    ),
    True: _PriceTableSpec(
        schema="market_data",
        table="adj_daily_prices",
        columns=ADJ_PRICE_COLUMNS,
    ),
}

def _get_init_func(*, schema_name):
        """拿到初始化数据库的函数, 后续在 `init_pg_schema()` 内统一调用初始化数据库"""
        with get_pgsql() as conn, conn.cursor() as cur:
            cur.execute()            # type: ignore[reportArgumentType]  # 来自可信的本地 schema 文件, 非拼接字符串
            logger.success(f"初始化 {schema_name} 表成功")
        

# 初始化数据库
def init_pg_schema() -> None:
    """在同一个 PostgreSQL 事务里初始化原始价表和复权价表。"""

    schema_statements = [
        SCHEMA_OLCHV.read_text(encoding="utf-8"),
        SCHEMA_OLCHV_ADJ.read_text(encoding="utf-8")
    ]

    try:
        with get_pgsql() as conn, conn.cursor() as cur:
            for statement in schema_statements:
                cur.execute(statement)          # type: ignore[reportArgumentType]  # 来自可信的本地 schema 文件, 非拼接字符串
    except psycopg.errors as exc:
        raise sc



    logger.success(
        "成功初始化两个数据库表格:"
        "[market_data.daily_prices], [market_data.adj_daily_prices]"
    )


def _build_upsert_sql(table: str, col: list[str]) -> str:
    """拼一条 upsert SQL, 长这样(以 daily_prices 为例, 省略了中间几列):

        INSERT INTO market_data.daily_prices (ticker, trade_date, open, ...)
        VALUES (%s, %s, %s, ...)
        ON CONFLICT (ticker, trade_date) DO UPDATE SET
            open = EXCLUDED.open, ...

    EXCLUDED 指"这次想插入、但因为主键冲突被拒绝的那一行"——
    `col = EXCLUDED.col` 就是"用这次抓到的新值覆盖旧值"。
    ticker/trade_date 是主键, 冲突判断靠它俩, 不需要(也不能)出现在 SET 里。
    """
    ...



def load_prices(prices: pd.DataFrame,
                *,
                adjusted: bool) -> int:
    """把一批行情写入库, 用 upsert: 同一个 (ticker, trade_date) 已存在就更新, 不存在就插入

    为什么不能用普通 INSERT:
        两张表都是 PRIMARY KEY (ticker, trade_date), 重跑脚本 / 增量窗口有重叠时
        必然会撞到已存在的 (ticker, trade_date), 触发 UniqueViolation, 整批回滚。

    为什么不能用 ON CONFLICT DO NOTHING:
        Yahoo 会追溯修改历史 adj_close(除权除息事件确认后), 同一个 trade_date
        再抓一次数值可能变了, DO NOTHING 会把这种修正静默吞掉。
        所以用 DO UPDATE。
    """

    table = "market_data.adj_daily_prices" if adjusted else "market_data.daily_prices"

    if adjusted:
        cols = ["ticker", "trade_date", "open", "high", "low", "close", "volume"]
    else:
        cols = ["ticker", "trade_date", "open", "high", "low", "close",
                "adj_close", "volume", "dividends", "stock_splits"]

    ...

    



if __name__ == "__main__":
    ...