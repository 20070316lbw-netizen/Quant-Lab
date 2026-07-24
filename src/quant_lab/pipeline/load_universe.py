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
    members = fetch_sp500_universe()
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
