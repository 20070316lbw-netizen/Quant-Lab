from __future__ import annotations

from loguru import logger

from pipeline.config import SP500_CACHE_PATH, DATABASE_PATH, get_duckdb
from pipeline.storage.duckdb_store import init_schema, upsert
from pipeline.source.yahoo import YahooPrices
from pipeline.source.fetch_universe import SP500Universe


def build(ticker_limit: int = 503, period: str = "10y") -> None:
    """
    Args:
        tickers_limit: 取成分股前 N 只。FF3 横截面排序要足够多的名字才有意义,
                       默认 100; 想全量就传 503。
        period: yfinance 周期。FF3 按 6 月年度调仓, 要多年历史, 默认 '10y'。
    """

    DATABASE_PATH.parent.mkdir(parents = True, exist_ok = True)

    universe = SP500Universe().fetch()
    universe.to_csv(SP500_CACHE_PATH, index=False)
    logger.info(f"universe 已缓存到 {SP500_CACHE_PATH}")

    sample = universe.head(ticker_limit)
    total = len(sample)

    with get_duckdb() as con:
        init_schema(con)

        for i, row in enumerate(sample.itertuples(index=False), start=1):
            logger.info(f"[{i} / {total}]   {row.ticker}")

            try:
                prices = YahooPrices(row.ticker, period=period).fetch()
                upsert(con, "prices", prices)
                # TODO: 这块还需理解
                # TODO: 后续可加 EDGAR 数据内容

            except Exception as e:
                logger.error(f"{row.ticker} 存取失败, 跳过: {e}")

    logger.success("build SUCCESSFUL !!!")

if __name__ == "__main__":
    build()