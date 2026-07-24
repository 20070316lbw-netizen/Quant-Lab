"""数据库内代码为 RangeIndex , 为了让数据转化为 MultIndex, 我们在此采取只读策略输出 df"""
from __future__ import annotations

from pprint import pprint
from typing import Literal

import pandas as pd
from pydantic import BaseModel, field_validator

from quant_lab.connection import get_duckdb
from quant_lab.data.schema_registry import TABLES

"""
Literal 非常坑:
    * Literal[...] 只能写“字面量”
    * 不能塞变量
    * 不能引用 runtime dict
    * 不能动态展开

为什么有 Literal 呢, 因为他设计出来是为了给类型检查器 (mypy / pyright) 看的 “编译期信息”
而不是运行时逻辑, 同理,他不做检查,因此要求:
    * 必须是 静态可解析的值
    * 不能依赖变量（因为变量在运行时才知道）

所以我们我们不能直接 `Literal{TABLES}`

设计分三层:
    * 表是第一层分类 (Table)        -- src/quant_lab/data/schema_registry.py

    * 字段是第二层约束 (Schema)
        * 不能用动态 Literal

    * 查询对象是第三层 (Request)

    * 所有关系“只在一个地方定义”
"""
TableName = Literal["prices"]       # 对应 Table 约束, 入口白名单


# 第三层 Request, 查询请求对象, 在请求进入数据库之前做结构化检查
# 从 `prices` 中, 在某个日期范围内取某些字段
class RangeQuery(BaseModel):
    table:      TableName       # 合法值只有 `price`
    columns:    list[str]
    start:      str
    end:        str

    # 逻辑校验 (依赖 TABLES), `columns` 的合法性不是固定, 而是取决于 `table`
    # `columns` 应该根据 `table` 去 `TABLE` 里面找对应 `schema`
    @field_validator("columns")
    @classmethod
    def validate_columns(cls, v, info) -> list | str:
        table = info.data.get("table")

        if not table or table not in TABLES:
            return v

        schema = TABLES[table]      # 确认哪张表, 再拿出规则检查传入字段是否属于它

        invalid = [c for c in v if c not in schema.columns]
        if invalid:
            raise ValueError(f"{table} 不支持字段: {invalid}")

        return v


    @property
    def select_columns(self) -> list:
        schema = TABLES[self.table]
        return list(dict.fromkeys(schema.index + self.columns))



def build_sql(req: RangeQuery) -> str:
    schema = TABLES[req.table]
    cols = ", ".join(req.select_columns)

    # 我们的入库顺序是: ["date", "ticker", "open", "high", "low", "close", "volume"]
    # 第一个是时间列, 第二个是代码列
    # 动态获取索引
    date_col = schema.index[0]
    ticker_col = schema.index[1]

    return f"""
        SELECT {cols}
        FROM {schema.name}
        WHERE {date_col} BETWEEN ? AND ?
        ORDER BY {date_col}, {ticker_col}
    """

def loader(req: RangeQuery):
    with get_duckdb(read_only=True) as con:
        sql = build_sql(req)
        df = con.execute(sql, [req.start, req.end]).df()

        return df.set_index(TABLES[req.table].index)
    

def load_price_panel(
        start       : str   = "2016-06-30",
        end         : str   = "2026-06-30",
        date_col    : str   = "date",
        ticker_col  : str   = "ticker"
) -> pd.DataFrame:
    """读取 prices 表全部行情字段, 做类型转换后设置两层 index (date, ticker)

    注意: loader() 内部已经把 date/ticker 设成了 index (见 TABLES[table].index),
    所以这里拿到的 df 是没有 date/ticker 列的, 要用 index.get_level_values 取值,
    不能再用 df["date"] 这种写法(会 KeyError)。
    """
    schema = TABLES["prices"]

    # --------------------------- 数据读取,             return df
    # select_columns 会自动把 index 列(date/ticker)拼进去, 这里只需要传
    # 非 index 的行情字段(open/high/low/close/volume), 否则会漏掉真正的数据列
    price_columns = [c for c in schema.columns if c not in schema.index]

    req = RangeQuery(
        table=schema.name,
        columns=price_columns,
        start=start,
        end=end,
    )
    df = loader(req)
    # ---------------------------

    # --------------------------- 类型转换 + 重建 MultIndex   return df
    dates   = pd.to_datetime(df.index.get_level_values(date_col))
    tickers = df.index.get_level_values(ticker_col).astype("category")

    df.index = pd.MultiIndex.from_arrays([dates, tickers], names=[date_col, ticker_col])
    df = df.sort_index()

    return df


if __name__ == "__main__":
    df = load_price_panel()
    pprint(df)
    




