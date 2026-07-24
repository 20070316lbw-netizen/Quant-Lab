"""统一 schema 初始化。

项目所有业务表的 DDL 都放在仓库根目录的 db/schema/*.sql。
DuckDB 和 PostgreSQL 都从这里读取,不再允许某张表偷偷把 CREATE TABLE
塞在 Python 文件里,否则两个数据库的字段迟早会发生分歧。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import psycopg

from quant_lab.config import PROJECT_ROOT
from quant_lab.error import SchemaInitializationError
from quant_lab.storage.backend import DatabaseTarget, connect, validate_target

SCHEMA_DIR = PROJECT_ROOT / "db" / "schema"

# 这里只捕获"数据库驱动明确告诉我们执行失败"的异常。
# TypeError、AttributeError 等编程错误不能包装成数据库错误,否则真正的 bug 会被藏起来。
_DATABASE_ERRORS = (duckdb.Error, psycopg.Error)


def _schema_files(schema_dir: Path = SCHEMA_DIR) -> list[Path]:
    """按文件名顺序返回 schema 文件。

    因此文件使用 0001_、0002_ 前缀:字典序就是执行顺序。
    """
    files = sorted(schema_dir.glob("*.sql"))
    if not files:
        raise SchemaInitializationError(
            f"schema 目录中没有 SQL 文件: {schema_dir}"
        )
    return files


def initialize_schema(target: DatabaseTarget) -> None:
    """显式初始化目标数据库的全部表结构。

    SQL 文件按文件名排序执行。所有文件必须是幂等定义，以便该函数可以安全重跑。

    为什么不在 get_duckdb()/get_pgsql() 中自动建表:
    连接和建表是两件不同的事。查询脚本只想连接时,不应该顺手修改数据库结构。
    """
    validated_target = validate_target(target)

    # 先把全部 SQL 读进内存,再连接数据库。
    # 如果某个文件损坏/无权限,此时数据库事务还没开始,不会出现"执行了一半才发现
    # 下一份 SQL 读不出来"的尴尬状态。
    try:
        statements = [
            schema_file.read_text(encoding="utf-8")
            for schema_file in _schema_files()
        ]
    except (OSError, UnicodeError) as exc:
        raise SchemaInitializationError(
            f"读取 schema SQL 失败: {exc}"
        ) from exc

    connection = None

    # committed 是事务是否已经成功落盘的标记。
    # 不能只在 except 里 rollback,因为非数据库异常也可能出现在事务中间;
    # finally + committed 可以覆盖所有没有提交成功的退出路径。
    committed = False

    try:
        connection = connect(validated_target)

        # 两个数据库都显式开启事务:
        # 要么所有 schema 文件一起成功,要么一个都不生效。
        connection.execute("BEGIN")
        for statement in statements:
            connection.execute(statement)
        connection.commit()
        committed = True
    except _DATABASE_ERRORS as exc:
        # from exc 保留原始 duckdb/psycopg 异常链。
        # 上层看到项目错误的同时,仍能追到数据库给出的真正原因。
        raise SchemaInitializationError(
            f"{validated_target} schema 初始化失败: {exc}"
        ) from exc
    finally:
        if connection is not None:
            if not committed:
                try:
                    connection.rollback()
                except _DATABASE_ERRORS:
                    # 原始执行错误比 rollback 的二次错误更重要,这里不让它覆盖原异常。
                    pass
            connection.close()
