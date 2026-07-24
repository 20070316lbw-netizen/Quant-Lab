from __future__ import annotations

from pathlib import Path

from quant_lab.config import PROJECT_ROOT
from quant_lab.error import SchemaInitializationError
from quant_lab.storage.backend import DatabaseTarget, connect, validate_target

SCHEMA_DIR = PROJECT_ROOT / "db" / "schema"


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
    connection = None

    try:
        connection = connect(validated_target)
        connection.execute("BEGIN")
        for schema_file in _schema_files():
            connection.execute(schema_file.read_text(encoding="utf-8"))
        connection.commit()
    except SchemaInitializationError:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise SchemaInitializationError(
            f"{validated_target} schema 初始化失败: {exc}"
        ) from exc
    finally:
        if connection is not None:
            connection.close()
