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
from quant_lab.error import SchemaInitializationError, YahooLoadError
from quant_lab.sources.yahoo.columns import (
    ADJ_PRICE_COLUMNS,
    RAW_PRICE_COLUMNS,
)
from quant_lab.sources.yahoo.fetch import fetch_sp500_prices


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

# 两张表的主键都是 PRIMARY KEY (ticker, trade_date)(见 db/schema/0002、0003),
# upsert 冲突判断固定用这两列, 不跟着 spec.columns 走 —— spec.columns 是
# "要写哪些字段", 跟"用什么判断冲突"是两件事, 混在一起以后改字段顺序容易
# 连带改错冲突列。
_CONFLICT_COLUMNS = {"ticker", "trade_date"}

def _build_upsert_sql(spec: _PriceTableSpec) -> sql.Composed:
    """
    按表规格拼接出 upsert 语句:
        INSERT ... ON CONFLICT (ticker, trade_date) DO UPDATE

    调用示例:
        upsert_sql = _build_upsert_sql(spec)

    此处用 psycopg.sql 代替 f-string 拼接字符串:
        schema/table/column 名字都是 SQL 标识符(identifier), 不是数据值。
        sql.Identifier() 会自动加引号、转义特殊字符, 是 psycopg 官方推荐的
        "动态拼标识符"写法。真正的数据(每一行的值)完全不在这个函数里出现,
        全部走 %s 占位符参数化, 在 load_prices() 里通过 executemany 传入,
        没有 SQL 注入风险。
    """
    update_columns = [c for c in spec.columns if c not in _CONFLICT_COLUMNS]

    return sql.SQL(
        "INSERT INTO {schema}.{table} ({cols}) VALUES ({placeholders}) "
        "ON CONFLICT ({conflict_cols}) DO UPDATE SET {updates}"
    ).format(
        schema=sql.Identifier(spec.schema),
        table=sql.Identifier(spec.table),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in spec.columns),
        placeholders=sql.SQL(", ").join(
            sql.Placeholder() for _ in spec.columns
        ),
        conflict_cols=sql.SQL(", ").join(
            sql.Identifier(c) for c in _CONFLICT_COLUMNS
        ),
        updates=sql.SQL(", ").join(
            sql.SQL("{col} = EXCLUDED.{col}").format(col=sql.Identifier(c))
            for c in update_columns
        ),
    )
    """
    1. sql.SQL() 用来包装确定可信的 SQL 结构，例如：
    INSERT INTO
    VALUES
    ON CONFLICT
    DO UPDATE SET
    EXCLUDED
    这里的 {schema}、{table} 等不是数据库数据占位符，
    而是等待 .format() 填入的“SQL 结构占位符”。
    注意: sql.SQL() 不会转义内容，所以只应该放开发者自己写的固定 SQL, 不能直接放用户输入

    2. .format()：把 SQL 片段填进模板

    3. sql.Identifier()：处理表名、字段名等标识符, Identifier 专门用于: schema 名, 表名, 字段名, 索引名, 约束名
    例如: sql.Identifier("ticker")
    得到："ticker"

    4. sql.SQL(", ").join(...)：拼接多个 SQL 片

    5. sql.Placeholder()：生成数据占位符 %s
    Placeholder() 不会立即把数据放进 SQL。真实数据要稍后传给: 
    cur.execute(query, values)
    或者：
    cur.executemany(query, rows)
    其实这块很适合加上 map() 函数 把一个函数应用到可迭代对象（如列表）的每一个元素上，返回一个新的迭代器（惰性求值）
    基本语法
    ```python
    map(function, iterable, ...)
    function: 要应用的函数
    iterable: 一个或多个可迭代对象（列表、元组等）
    ```
    注意到他只能遍历一次, 所以记住: 能被 for 循环遍历的东西，
    基本都能直接扔进 join()、sum()、list() 这些函数里，不用先转成列表。
    map()、生成器表达式、range()、文件对象……只要你能写 for x in 它: ，那它就能直接用而不要转成列表
    只转 list()，当你需要：
    用 for 循环遍历两次以上（比如先算一次总数，再遍历一次打印）
    用下标取值，比如 data[0]
    用 len() 看长度
    想直接 print() 出内容看看长啥样（这个是纯粹为了调试方便）
    其他情况——直接传，不用转。

    6. EXCLUDED 是 PostgreSQL 在 ON CONFLICT 中提供的特殊名称，
    表示“本来准备插入、但发生冲突的那条新数据”。
    """


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
    except psycopg.Error as exc:
        raise SchemaInitializationError(f"Yahoo 价格表初始化失败: {exc}") from exc

    logger.success(
        "成功初始化两个数据库表格:"
        "[market_data.daily_prices], [market_data.adj_daily_prices]"
    )


def load_prices(prices: pd.DataFrame,
                *,
                adjusted: bool
                ) -> int:
    """把一批行情写入库, 用 upsert: 同一个 (ticker, trade_date) 已存在就更新, 不存在就插入
   
    因为 0002 和 0003 schema 都有:
        PRIMARY KEY (ticker, trade_date)
    所以用的不是普通的 INSERT
    """

    if not isinstance(adjusted, bool):
        raise TypeError("adjusted 必须是 bool")

    spec = _PRICE_TABLE_SPECS[adjusted]     # 用查表的方法来找对应配置

    missing = [c for c in spec.columns if c not in prices.columns]
    if missing:
        raise YahooLoadError(
            f"{spec.schema}.{spec.table} 写入失败: Dataframe 缺少字段 {missing}"
        )

    if prices.empty:
        logger.warning(f"{spec.schema}.{spec.table}: 传入空的 Dataframe, 跳过写入")
        return 0

    # 按 spec.columns 的顺序重新选列, 不依赖调用方传进来的 DataFrame 列顺序 ——
    # itertuples() 转出来的 tuple 位置必须跟 SQL 里 %s 占位符的顺序严格对应,
    # 提前用 spec.columns 对齐, 比要求调用方"自己保证列顺序对"更可靠。
    rows = list(
        prices[list(spec.columns)].itertuples(index=False, name=None)
    )

    upsert_sql = _build_upsert_sql(spec)

    try:
        with get_pgsql() as conn, conn.cursor() as cur:
            cur.executemany(upsert_sql, rows)
            """
            executemany(sql语句, 参数序列) 会对参数序列里的每一个元素都执行一次那条 SQL,
            相当于循环调用 execute,但通常能更高效地批量提交。
            第二个参数是参数序列(一个可迭代对象,每个元素是一组要绑定到 SQL 语句里占位符的参数)
            """

    except psycopg.Error as exc:
        raise YahooLoadError(f"{spec.schema}.{spec.table} 写入失败: {exc}") from exc

    logger.success(f"{spec.schema}.{spec.table} upsert {len(rows)} 行")

    return len(rows)

def load_sp500_prices(*, adjusted: bool) -> int:
    """编排层: 抓整个 sp500 universe 的价格, 再写入对应的表。

    跟 fetch_sp500_prices() 一样不设默认值 —— 未复权/已复权是两张结构不同的表,
    强制显式传, 理由跟 Yahoo.fetch() 里那条一致(不给默认值, 避免手滑漏传)。
    """   

    prices = fetch_sp500_prices(adjusted=adjusted)
    return load_prices(prices, adjusted=adjusted)

if __name__ == "__main__":
    init_pg_schema()

    raw_count = load_sp500_prices(adjusted=False)
    adj_count = load_sp500_prices(adjusted=True)

    logger.success(
        f"入库完成: 未复权 {raw_count} 行, 已复权 {adj_count} 行"
    )


