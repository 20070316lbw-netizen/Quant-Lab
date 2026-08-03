"""PostgreSQL 只读查询层使用的表结构注册表。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from quant_lab.config import ADJ_PRICE_COLUMNS, INDEX_COLUMNS, RAW_PRICE_COLUMNS

ValidTableName = Literal["adj_daily_prices", "daily_prices"]

# 手动定义合法的查询范围
@dataclass(frozen=True)
class ValidName:
    place       : str           # 查询的表在哪个位置
    name        : str           # 查询的表叫什么名字
    columns     : list[str]     # 查询的列
    index       : list[str]     # 查询的索引


VALID: dict[str, ValidName] = {
    "adj_daily_prices":
        ValidName(
            place="market_data",
            name="adj_daily_prices",
            columns=list(ADJ_PRICE_COLUMNS),
            index=INDEX_COLUMNS
        ),
    "daily_prices":
        ValidName(
            place="market_data",
            name="daily_prices",
            columns=list(RAW_PRICE_COLUMNS),
            index=INDEX_COLUMNS
        )
}


