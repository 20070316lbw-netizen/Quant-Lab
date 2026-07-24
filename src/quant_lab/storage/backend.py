"""数据库目标的公共类型,以及最薄的一层连接分发。

这个文件故意不放建表、查询、事务等逻辑。
它只回答一个问题:"调用方指定 duckdb/postgres 后,到底该拿哪种连接?"
这样上层存储代码不用到处重复 if target == ...。
"""

from __future__ import annotations

from typing import Literal, TypeAlias, cast

from quant_lab.connection import get_duckdb, get_pgsql

# Literal 不负责运行时校验,它主要是给编辑器/类型检查器看的:
# 写成 target="mysql" 时,编辑器能提前提示错误。
# 真正的运行时检查仍然由下面的 validate_target() 完成。
DatabaseTarget: TypeAlias = Literal["postgres", "duckdb"]

# frozenset 是不可修改的集合。
# 这里不希望运行过程中有人意外 append/add 一个未实现的数据库类型。
_DATABASE_TARGETS = frozenset({"postgres", "duckdb"})


def validate_target(target: str) -> DatabaseTarget:
    """在真正连接数据库之前,拒绝不支持的 target。

    返回时使用 cast 告诉类型检查器:
    经过上面的集合检查后,这个普通 str 已经可以安全视为 DatabaseTarget。
    cast 只影响静态类型,运行时不会转换或修改 target。
    """
    if target not in _DATABASE_TARGETS:
        choices = ", ".join(sorted(_DATABASE_TARGETS))
        raise ValueError(f"不支持的数据库目标 {target!r}; 可选值: {choices}")
    return cast(DatabaseTarget, target)


def connect(target: DatabaseTarget, *, read_only: bool = False):
    """根据 target 选择连接工厂,但不替调用方建表或开启事务。"""
    if target == "duckdb":
        return get_duckdb(read_only=read_only)
    return get_pgsql(read_only=read_only)
