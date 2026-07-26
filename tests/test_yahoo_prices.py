from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from quant_lab.sources.yahoo.fetch import OHLCV_COLUMNS, OHLCV_COLUMNS_ADJ, Yahoo


def test_get_prices_uses_trade_date_and_adj_close(monkeypatch) -> None:
    raw = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [110.0],
            "Low": [95.0],
            "Close": [105.0],
            "Adj Close": [104.0],
            "Volume": [1_000],
            "Dividends": [0.0],
            "Stock Splits": [0.0],
        },
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
    )

    class FakeTicker:
        def history(self, period: str, *, auto_adjust: bool) -> pd.DataFrame:
            assert period == "10y"
            assert auto_adjust is False
            return raw

    monkeypatch.setattr(
        "quant_lab.sources.yahoo.fetch.yf.Ticker",
        lambda ticker: FakeTicker(),
    )

    prices = Yahoo(ticker="AAPL")._get_prices()

    assert list(prices.columns) == OHLCV_COLUMNS
    assert prices.loc[0, "trade_date"] == date(2026, 1, 2)
    assert prices.loc[0, "ticker"] == "AAPL"
    assert prices.loc[0, "adj_close"] == 104.0


def test_price_schemas_keep_raw_and_adjusted_prices_separate() -> None:
    schema_paths = (
        Path("db/schema/0002_sp500_prices.sql"),
        Path("db/schema/0003_sp500_adj_prices.sql"),
    )

    with duckdb.connect(":memory:") as conn:
        for schema_path in schema_paths:
            conn.execute(schema_path.read_text(encoding="utf-8"))

        raw_columns = [
            row[0]
            for row in conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'market_data'
                  AND table_name = 'daily_prices'
                ORDER BY ordinal_position
                """
            ).fetchall()
        ]
        adjusted_columns = [
            row[0]
            for row in conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'market_data'
                  AND table_name = 'adj_daily_prices'
                ORDER BY ordinal_position
                """
            ).fetchall()
        ]

    assert raw_columns == OHLCV_COLUMNS
    assert adjusted_columns == OHLCV_COLUMNS_ADJ
