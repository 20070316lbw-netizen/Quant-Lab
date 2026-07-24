"""显式初始化 PostgreSQL 或 DuckDB schema。"""

from __future__ import annotations

import argparse

from loguru import logger

from quant_lab.storage import initialize_schema


def main() -> None:
    # argparse 是 Python 标准库的命令行参数解析器。
    # choices 同时生成帮助文字和运行时校验,传 --target mysql 会直接被拒绝。
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

    # 这里只负责把 CLI 参数交给存储模块。
    # 真正的文件读取、事务和错误翻译都封装在 initialize_schema() 里面。
    initialize_schema(args.target)
    logger.success("{} schema 初始化完成", args.target)


if __name__ == "__main__":
    main()
