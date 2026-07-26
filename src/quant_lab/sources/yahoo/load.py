"""S&P 500 全体股票抓取入库

数据库: DuckDB
"""

from __future__ import annotations

from quant_lab.config import SCHEMA_OLCHV, SCHEMA_OLCHV_ADJ
from quant_lab.connection import get_duckdb


# 原始价格和复权价格分表存放,因此初始化时两份 DDL 必须一起执行。
def init_duckdb_schema() -> None:
    with get_duckdb() as conn:
        for schema_path in (SCHEMA_OLCHV, SCHEMA_OLCHV_ADJ):
            schema_sql = schema_path.read_text(encoding="utf-8")
            conn.execute(schema_sql)  # type: ignore[reportArgumentType]



if __name__ == "__main__":
    init_duckdb_schema()
