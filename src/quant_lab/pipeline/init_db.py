"""显式初始化 PostgreSQL 或 DuckDB schema。"""

from __future__ import annotations

import argparse

from loguru import logger

from quant_lab.storage import initialize_schema


def main() -> None:
    parser = argparse.ArgumentParser(
        description="初始化 Quant Lab 数据库 schema",
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=("postgres", "duckdb"),
        help="要初始化的目标数据库",
    )
    args = parser.parse_args()
    initialize_schema(args.target)
    logger.success("{} schema 初始化完成", args.target)


if __name__ == "__main__":
    main()
