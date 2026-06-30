"""数据库内代码为 RangeIndex , 为了让数据转化为 MultIndex, 我们在此采取只读策略输出 df"""
from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, field_validator

from quant_lab.config import get_duckdb
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
