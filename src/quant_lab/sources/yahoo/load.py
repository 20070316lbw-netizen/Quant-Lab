"""S&P 500 全体股票抓取入库

数据库: PostgreSQL
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from quant_lab.config import SCHEMA_OLCHV, SCHEMA_OLCHV_ADJ
from quant_lab.connection import get_pgsql

schema_02_sql = SCHEMA_OLCHV.read_text(encoding="utf-8")
schema_03_sql = SCHEMA_OLCHV_ADJ.read_text(encoding="utf-8")

def _get_init_func(*, schema_name):
        """拿到初始化数据库的函数, 后续在 `init_pg_schema()` 内统一调用初始化数据库"""
        with get_pgsql() as conn, conn.cursor() as cur:
            cur.execute()            # type: ignore[reportArgumentType]  # 来自可信的本地 schema 文件, 非拼接字符串
            logger.success(f"初始化 {schema_name} 表成功")
        

# 初始化数据库
def init_pg_schema() -> None:
     with get_pgsql() as conn:
        with conn.cursor() as cur1:
            cur1.execute(schema_02_sql)         # type: ignore[reportArgumentType]  # 来自可信的本地 schema 文件, 非拼接字符串
        with conn.cursor() as cur2:
            cur2.execute(schema_03_sql)         # type: ignore[reportArgumentType]  # 来自可信的本地 schema 文件, 非拼接字符串

     logger.success("成功初始化两个数据库表格: [market_data.daily_prices], [market_data.adj_daily_prices]")


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

    



if __name__ == "__main__":
    ...