from __future__ import annotations

from typing import Literal, TypeAlias, cast

from quant_lab.connection import get_duckdb, get_pgsql

DatabaseTarget: TypeAlias = Literal["postgres", "duckdb"]

_DATABASE_TARGETS = frozenset({"postgres", "duckdb"})


def validate_target(target: str) -> DatabaseTarget:
    if target not in _DATABASE_TARGETS:
        choices = ", ".join(sorted(_DATABASE_TARGETS))
        raise ValueError(f"不支持的数据库目标 {target!r}; 可选值: {choices}")
    return cast(DatabaseTarget, target)


def connect(target: DatabaseTarget, *, read_only: bool = False):
    if target == "duckdb":
        return get_duckdb(read_only=read_only)
    return get_pgsql(read_only=read_only)
