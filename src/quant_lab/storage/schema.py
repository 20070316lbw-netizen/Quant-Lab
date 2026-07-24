from __future__ import annotations

from pathlib import Path

import duckdb
import psycopg

from quant_lab.config import PROJECT_ROOT
from quant_lab.error import SchemaInitializationError
from quant_lab.storage.backend import DatabaseTarget, connect, validate_target

SCHEMA_DIR = PROJECT_ROOT / "db" / "schema"
_DATABASE_ERRORS = (duckdb.Error, psycopg.Error)


def _schema_files(schema_dir: Path = SCHEMA_DIR) -> list[Path]:
    files = sorted(schema_dir.glob("*.sql"))
    if not files:
        raise SchemaInitializationError(
            f"schema 目录中没有 SQL 文件: {schema_dir}"
        )
    return files


def initialize_schema(target: DatabaseTarget) -> None:
    """显式初始化目标数据库的全部表结构。

    SQL 文件按文件名排序执行。所有文件必须是幂等定义，以便该函数可以安全重跑。
    """
    validated_target = validate_target(target)
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
    committed = False

    try:
        connection = connect(validated_target)
        connection.execute("BEGIN")
        for statement in statements:
            connection.execute(statement)
        connection.commit()
        committed = True
    except _DATABASE_ERRORS as exc:
        raise SchemaInitializationError(
            f"{validated_target} schema 初始化失败: {exc}"
        ) from exc
    finally:
        if connection is not None:
            if not committed:
                try:
                    connection.rollback()
                except _DATABASE_ERRORS:
                    pass
            connection.close()
