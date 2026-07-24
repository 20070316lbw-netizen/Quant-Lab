from __future__ import annotations

import pandas as pd
from loguru import logger

from quant_lab.config import SP500_CACHE_PATH
from quant_lab.connection import get_duckdb
from quant_lab.error import QuantLabError
from quant_lab.sources.universe import fetch_sp500_universe
from quant_lab.sources.yahoo import YahooPrices
from quant_lab.storage.duckdb_store import upsert


def build(ticker_limit: int = 503, period: str = "10y") -> None:
    """
    Args:
        # TODO: 参数名是 ticker_limit，但文档写成 tickers_limit，后续需要统一
        tickers_limit: 取成分股前 N 只。FF3 横截面排序要足够多的名字才有意义,
                       默认 100; 想全量就传 503。
        # TODO: 当前函数默认 ticker_limit=503，但文档说默认 100，后续需要修正文档或默认值
        period: yfinance 周期。FF3 按 6 月年度调仓, 要多年历史, 默认 '10y'。
    """

    # TODO: 当前每次 build 都重新抓 Wikipedia，后续可优先读取 SP500_CACHE_PATH 并支持强制刷新
    universe = fetch_sp500_universe()
    universe_frame = pd.DataFrame(
        [member.model_dump() for member in universe]
    )
    universe_frame.to_csv(SP500_CACHE_PATH, index=False)
    logger.info(f"universe 已缓存到 {SP500_CACHE_PATH}")

    # TODO: ticker_limit 未校验，传入 0/负数/超过 universe 长度时行为需要明确
    sample = universe[:ticker_limit]
    total = len(sample)
    succeeded = 0
    failed = 0

    with get_duckdb() as con:
        # TODO: 当前串行抓取 503 只股票会比较慢，后续可考虑限速并发或断点续跑
        for i, member in enumerate(sample, start=1):
            logger.info(f"[{i} / {total}]   {member.ticker}")

            try:
                prices = YahooPrices(member.ticker, period=period).fetch()
                # TODO: 确认 upsert 的主键/冲突策略，避免重复 build 时产生重复行情数据
                upsert(con, "prices", prices)
                # TODO: 这块还需理解
                # TODO: 后续可加 EDGAR 数据内容
                succeeded += 1

            except QuantLabError as exc:
                failed += 1
                logger.error(f"{member.ticker} 存取失败, 跳过: {exc}")

    logger.success(
        "prices build 完成: 成功 {}, 失败 {}",
        succeeded,
        failed,
    )

if __name__ == "__main__":
    build()
