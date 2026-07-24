"""抓取并写入当前 S&P 500 universe 快照。"""

from __future__ import annotations

import argparse

from loguru import logger

from quant_lab.sources.universe import fetch_sp500_universe
from quant_lab.storage import (
    DatabaseTarget,
    UniverseLoadResult,
    load_sp500_universe,
)


def sync_sp500_universe(
    *,
    target: DatabaseTarget,
) -> UniverseLoadResult:
    """组合抓取模块和存储模块,但不隐藏目标数据库。

    这里是 composition root(组装入口):
    fetch 只认识外部数据源,load 只认识数据库,由 pipeline 把两者接起来。
    """

    # 先完整抓取并校验;抓取模块只要发现一条坏记录就会 raise,
    # 因此残缺快照不会进入下面的精确同步。
    members = fetch_sp500_universe()

    # 不在这里自动 initialize_schema(),也不自动同时写两个数据库。
    # 建表和选择目标都是调用者必须明确做出的动作。
    result = load_sp500_universe(members, target=target)
    logger.success(
        "sp500_universe -> {}: received={}, inserted={}, updated={}, "
        "unchanged={}, deleted={}",
        result.target,
        result.received,
        result.inserted,
        result.updated,
        result.unchanged,
        result.deleted,
    )
    return result


def main() -> None:
    # required=True 是刻意的:
    # PostgreSQL 是主库,不能因为一个默认值让脚本在不知情时写错数据库。
    parser = argparse.ArgumentParser(
        description="抓取并同步当前 S&P 500 universe",
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=("postgres", "duckdb"),
        help="本次写入的唯一目标数据库",
    )
    args = parser.parse_args()
    sync_sp500_universe(target=args.target)


if __name__ == "__main__":
    main()
