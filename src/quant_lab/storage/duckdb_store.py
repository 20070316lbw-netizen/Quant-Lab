from __future__ import annotations

import duckdb
import pandas as pd
from loguru import logger

# TODO: 还没有理解这个方法的大部分组件方法
def upsert(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> None:
    """把 df 幂等写入指定表。

    INSERT OR REPLACE + 主键 = 重复跑 pipeline 不会产生重复行(已存在的按主键覆盖)。
    要求 df 的列顺序和建表一致 —— 这个约束由各 DataSource 在 fetch() 里保证。
    """
    if df.empty:
        logger.warning(f"{table}: 收到空 DataFrame, 跳过写入")
        return
    # register 把本地 df 暴露成一张可被 SQL 扫描的临时视图; 用完 unregister 清理。
    con.register("_staging", df)
    try:
        con.execute(f"INSERT OR REPLACE INTO {table} SELECT * FROM _staging")
    finally:
        con.unregister("_staging")
    logger.success(f"{table}: 写入/更新 {len(df)} 行")
