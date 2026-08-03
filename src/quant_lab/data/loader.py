"""从 PostgreSQL 读取研究数据，并整理成带业务索引的 DataFrame

原始输入
   ↓
model_validator(mode="before")     检查/整理整包原始数据
   ↓
field_validator(mode="before")     整理某个字段的原始值
   ↓
Pydantic 核心验证                 按类型注解转换、检查类型和 Field 约束
   ↓
field_validator(mode="after")      检查已经转换好的单个字段
   ↓
model_validator(mode="after")      检查字段之间的关系
   ↓
最终 BaseModel 对象
"""

from __future__ import annotations

from typing import Self

import pandas as pd
from loguru import logger
from psycopg import sql
from pydantic import BaseModel, field_validator, model_validator

from quant_lab.connection import get_pgsql
from quant_lab.data.schema_registry import VALID, ValidTableName


class Query(BaseModel):
    """
    查询内容填写
    
    place   : 表的位置, prices 类表的位置在 "market_data"
    name    : 查询的表名字, 通过 situa 定位后获得,
    columns : 查询表内的列
    start   : 查询开始日期
    end     : 查询结束日期

    包含对内容的检查:
        1. place:
            使用 @model_validator(mode="after")
            对表的位置进行检查, 在 VALID 内做校验, 若不通过则直接 raise

        2. name:
            使用 Literal 做检验

        3. columns:
            使用 @field_validator("columns") 做检验, 若不通过则直接 raise
    """
    place   : str
    name    : ValidTableName
    columns : list[str]
    start   : str
    end     : str

    @model_validator(mode="after")
    def _check_place(self) -> Self:
        """对 place 进行检查"""
        register_place = VALID[self.name].place
        logger.info(
            f"checking place: input={self.place!r}, "
            f"expected={register_place!r}"
        )

        if self.place != register_place:
            raise ValueError(
                f"`place` should be {register_place!r}"
            )

        logger.success(f"{self.place!r} PASSED !!!")
        return self


        
    @field_validator("columns")
    @classmethod
    def _check_columns(cls,
                       value: list[str],
                       info                 # 由 pydantic 提供
                       ) -> list:
        """对 columns 做检查"""

        checked_name = info.data.get("name")
        if checked_name is None:
            return value

        valid_columns = VALID[checked_name].columns
        invalid = [column for column in value if column not in valid_columns]

        if invalid:
            raise ValueError(
                f"{checked_name} not support {invalid}"
            )
        
        return value

def build_sql(request: Query) -> sql.Composed:
    """拼接需要的 SQL 语句"""

    table_info = VALID[request.name]
    request_columns = sql.SQL(", ").join(
        sql.Identifier(column) for column in request.columns
    )

    date_type, ticker = table_info.index

    return sql.SQL(
        "SELECT {ticker}, {date_type}, {columns} FROM {place}.{name} "
        "WHERE {date_type} BETWEEN %s AND %s "
        "ORDER BY {date_type}, {ticker} "
    ).format(
        columns     = request_columns,
        place       = sql.Identifier(table_info.place),
        name        = sql.Identifier(table_info.name),
        date_type   = sql.Identifier(date_type),
        ticker      = sql.Identifier(ticker),
    )

def loader(*, request: Query) -> pd.DataFrame:
    """以只读的形式查询并且返回 MultINdex DataFrame"""

    query = build_sql(request)

    with get_pgsql(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(query, (request.start, request.end))
        row = cur.fetchall()

    dataframe = pd.DataFrame(
        row,
        columns=["ticker", "trade_date", *request.columns],
        )

    return dataframe.set_index(["trade_date", "ticker"])

    
        


if __name__ == "__main__":
    query = Query(
        place="market_data",
        name="daily_prices",
        columns=["close", ],
        start="2025-01-01",
        end="2025-01-31",
    )
    logger.info(query)

    built_sql = build_sql(query)
    with get_pgsql(read_only=True) as conn, conn.cursor() as cur:
        check = built_sql.as_string(cur)
        logger.info(check)

    df = loader(request=query)
    print(df)
    
