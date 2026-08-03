from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import pandas.testing as pdt
import pytest
from pydantic import ValidationError

import quant_lab.data.loader as loader_module
from quant_lab.data.loader import Query, build_sql, loader


def make_query(*, columns: list[str] | None = None) -> Query:
    return Query(
        place="market_data",
        name="daily_prices",
        columns=columns or ["close"],
        start="2025-01-01",
        end="2025-01-31",
    )


def test_query_accepts_registered_table_and_columns() -> None:
    request = make_query(columns=["close", "volume"])

    assert request.name == "daily_prices"
    assert request.columns == ["close", "volume"]


def test_query_reports_invalid_table_name() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Query(
            place="market_data",
            name="prices",  # type: ignore[arg-type]
            columns=["close"],
            start="2025-01-01",
            end="2025-01-31",
        )

    assert exc_info.value.errors()[0]["loc"] == ("name",)
    assert "daily_prices" in str(exc_info.value)


def test_query_rejects_columns_outside_registered_table() -> None:
    with pytest.raises(ValidationError, match="daily_prices not support"):
        make_query(columns=["close", "unknown_column"])


def test_build_sql_uses_registered_table_and_date_range_placeholders() -> None:
    request = make_query()

    statement = " ".join(build_sql(request).as_string(None).split())

    assert statement == (
        'SELECT "ticker", "trade_date", "close" '
        'FROM "market_data"."daily_prices" '
        'WHERE "trade_date" BETWEEN %s AND %s '
        'ORDER BY "trade_date", "ticker"'
    )


def test_loader_returns_trade_date_ticker_multiindex(monkeypatch) -> None:
    rows = [
        ("AAPL", date(2025, 1, 2), 243.85, 1000),
        ("MSFT", date(2025, 1, 2), 418.79, 2000),
    ]

    class FakeCursor:
        def __enter__(self) -> FakeCursor:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execute(self, query: object, params: object) -> None:
            return None

        def fetchall(self) -> list[tuple[Any, ...]]:
            return rows

    class FakeConnection:
        def __enter__(self) -> FakeConnection:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def cursor(self) -> FakeCursor:
            return FakeCursor()

    def fake_get_pgsql(*, read_only: bool = False) -> FakeConnection:
        assert read_only is True
        return FakeConnection()

    monkeypatch.setattr(loader_module, "get_pgsql", fake_get_pgsql)

    result = loader(request=make_query(columns=["close", "volume"]))
    expected = pd.DataFrame(
        {"close": [243.85, 418.79], "volume": [1000, 2000]},
        index=pd.MultiIndex.from_tuples(
            [
                (date(2025, 1, 2), "AAPL"),
                (date(2025, 1, 2), "MSFT"),
            ],
            names=["trade_date", "ticker"],
        ),
    )

    pdt.assert_frame_equal(result, expected)
