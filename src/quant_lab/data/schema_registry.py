"""数据字典, 声明系统里面有哪些表,每张表有哪些字段, 内置 `TABLE` 作为运行时配置"""

from quant_lab.config import OHLCV_COLUMNS, INDEX_COLUMNS


from dataclasses import dataclass

@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: list[str]
    index: list[str]

# 单一数据源, 同时也是运行时配置
TABLES: dict[str, TableSchema] = {
    "prices": TableSchema(
        name    = "prices",
        columns = OHLCV_COLUMNS,
        index   = INDEX_COLUMNS
    ),
}
