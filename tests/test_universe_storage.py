from __future__ import annotations

import duckdb
import pytest
from pydantic import ValidationError

import quant_lab.connection as connection_module
from quant_lab.error import UniverseLoadError
from quant_lab.sources.universe import SP500UniverseMember
from quant_lab.storage import initialize_schema, load_sp500_universe


def member(ticker: str, company_name: str, cik: str) -> SP500UniverseMember:
    return SP500UniverseMember(
        ticker=ticker,
        company_name=company_name,
        cik=cik,
    )


@pytest.fixture
def duckdb_path(tmp_path, monkeypatch):
    path = tmp_path / "quant_lab.duckdb"
    monkeypatch.setattr(connection_module, "DATABASE_PATH", path)
    return path


def test_universe_member_normalizes_storage_identifiers():
    result = member(" brk.b ", " Berkshire Hathaway ", "1067983")

    assert result.ticker == "BRK-B"
    assert result.company_name == "Berkshire Hathaway"
    assert result.cik == "0001067983"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ticker", " "),
        ("company_name", " "),
        ("cik", ""),
        ("cik", "not-a-cik"),
        ("cik", "12345678901"),
    ],
)
def test_universe_member_rejects_invalid_fields(field, value):
    data = {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "cik": "320193",
    }
    data[field] = value

    with pytest.raises(ValidationError):
        SP500UniverseMember(**data)


def test_schema_initialization_is_idempotent_and_shared(duckdb_path):
    initialize_schema("duckdb")
    initialize_schema("duckdb")

    with duckdb.connect(str(duckdb_path), read_only=True) as con:
        tables = {
            row[0]
            for row in con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                """
            ).fetchall()
        }
        universe_columns = con.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'sp500_universe'
            ORDER BY ordinal_position
            """
        ).fetchall()
        price_columns = con.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'prices'
            ORDER BY ordinal_position
            """
        ).fetchall()

    assert {"sp500_universe", "prices"} <= tables
    assert universe_columns == [
        ("ticker",),
        ("company_name",),
        ("cik",),
    ]
    assert price_columns == [
        ("date",),
        ("ticker",),
        ("open",),
        ("high",),
        ("low",),
        ("close",),
        ("volume",),
    ]


def test_duckdb_load_exactly_synchronizes_current_snapshot(duckdb_path):
    initialize_schema("duckdb")

    first = load_sp500_universe(
        [
            member("AAPL", "Apple Inc.", "320193"),
            member("MSFT", "Microsoft Corp.", "789019"),
        ],
        target="duckdb",
    )

    assert first.target == "duckdb"
    assert first.received == 2
    assert first.inserted == 2
    assert first.updated == 0
    assert first.unchanged == 0
    assert first.deleted == 0

    second = load_sp500_universe(
        [
            member("AAPL", "Apple Incorporated", "320193"),
            member("NVDA", "NVIDIA Corp.", "1045810"),
        ],
        target="duckdb",
    )

    assert second.received == 2
    assert second.inserted == 1
    assert second.updated == 1
    assert second.unchanged == 0
    assert second.deleted == 1

    unchanged = load_sp500_universe(
        [
            member("AAPL", "Apple Incorporated", "320193"),
            member("NVDA", "NVIDIA Corp.", "1045810"),
        ],
        target="duckdb",
    )

    assert unchanged.inserted == 0
    assert unchanged.updated == 0
    assert unchanged.unchanged == 2
    assert unchanged.deleted == 0

    with duckdb.connect(str(duckdb_path), read_only=True) as con:
        rows = con.execute(
            """
            SELECT ticker, company_name, cik
            FROM sp500_universe
            ORDER BY ticker
            """
        ).fetchall()

    assert rows == [
        ("AAPL", "Apple Incorporated", "0000320193"),
        ("NVDA", "NVIDIA Corp.", "0001045810"),
    ]


def test_load_rejects_empty_snapshot_before_connecting(duckdb_path):
    with pytest.raises(UniverseLoadError, match="不能为空"):
        load_sp500_universe([], target="duckdb")

    assert not duckdb_path.exists()


def test_load_rejects_duplicate_tickers_without_changing_data(duckdb_path):
    initialize_schema("duckdb")
    load_sp500_universe(
        [member("AAPL", "Apple Inc.", "320193")],
        target="duckdb",
    )

    with pytest.raises(UniverseLoadError, match="重复 ticker"):
        load_sp500_universe(
            [
                member("AAPL", "Apple Inc.", "320193"),
                member("aapl", "Apple Incorporated", "320193"),
            ],
            target="duckdb",
        )

    result = load_sp500_universe(
        [member("AAPL", "Apple Inc.", "320193")],
        target="duckdb",
    )
    assert result.unchanged == 1


def test_duckdb_load_rolls_back_when_delete_fails(duckdb_path):
    initialize_schema("duckdb")
    load_sp500_universe(
        [
            member("AAPL", "Apple Inc.", "320193"),
            member("MSFT", "Microsoft Corp.", "789019"),
        ],
        target="duckdb",
    )

    with duckdb.connect(str(duckdb_path)) as con:
        con.execute(
            """
            CREATE TABLE universe_reference (
                ticker VARCHAR PRIMARY KEY,
                FOREIGN KEY (ticker) REFERENCES sp500_universe(ticker)
            )
            """
        )
        con.execute(
            "INSERT INTO universe_reference (ticker) VALUES ('MSFT')"
        )

    with pytest.raises(UniverseLoadError, match="写入 duckdb 失败"):
        load_sp500_universe(
            [member("AAPL", "Apple Incorporated", "320193")],
            target="duckdb",
        )

    with duckdb.connect(str(duckdb_path), read_only=True) as con:
        rows = con.execute(
            """
            SELECT ticker, company_name
            FROM sp500_universe
            ORDER BY ticker
            """
        ).fetchall()

    assert rows == [
        ("AAPL", "Apple Inc."),
        ("MSFT", "Microsoft Corp."),
    ]
