from __future__ import annotations

import os

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

import quant_lab.storage.backend as backend_module
from quant_lab.error import UniverseLoadError
from quant_lab.sources.universe import SP500UniverseMember
from quant_lab.storage import initialize_schema, load_sp500_universe

TEST_POSTGRES_DSN = os.environ.get("TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(
    TEST_POSTGRES_DSN is None,
    reason="需要显式设置 TEST_POSTGRES_DSN",
)


def member(ticker: str, company_name: str, cik: str) -> SP500UniverseMember:
    return SP500UniverseMember(
        ticker=ticker,
        company_name=company_name,
        cik=cik,
    )


@pytest.fixture
def postgres_test_database(monkeypatch):
    assert TEST_POSTGRES_DSN is not None
    database_name = conninfo_to_dict(TEST_POSTGRES_DSN).get("dbname", "")
    if "test" not in database_name.lower():
        pytest.fail(
            "TEST_POSTGRES_DSN 的数据库名必须包含 'test'，拒绝执行破坏性测试"
        )

    def connect_test_database(*, read_only=False):
        if read_only:
            return psycopg.connect(
                TEST_POSTGRES_DSN,
                options="-c default_transaction_read_only=on",
            )
        return psycopg.connect(TEST_POSTGRES_DSN)

    monkeypatch.setattr(backend_module, "get_pgsql", connect_test_database)

    with psycopg.connect(TEST_POSTGRES_DSN, autocommit=True) as con:
        con.execute("DROP TABLE IF EXISTS prices")
        con.execute("DROP TABLE IF EXISTS sp500_universe CASCADE")
        con.execute(
            "DROP FUNCTION IF EXISTS reject_universe_delete() CASCADE"
        )

    initialize_schema("postgres")
    yield

    with psycopg.connect(TEST_POSTGRES_DSN, autocommit=True) as con:
        con.execute("DROP TABLE IF EXISTS prices")
        con.execute("DROP TABLE IF EXISTS sp500_universe CASCADE")
        con.execute(
            "DROP FUNCTION IF EXISTS reject_universe_delete() CASCADE"
        )


def test_postgres_adapter_matches_universe_contract(postgres_test_database):
    first = load_sp500_universe(
        [
            member("AAPL", "Apple Inc.", "320193"),
            member("MSFT", "Microsoft Corp.", "789019"),
        ],
        target="postgres",
    )
    assert (
        first.inserted,
        first.updated,
        first.unchanged,
        first.deleted,
    ) == (2, 0, 0, 0)

    second = load_sp500_universe(
        [
            member("AAPL", "Apple Incorporated", "320193"),
            member("NVDA", "NVIDIA Corp.", "1045810"),
        ],
        target="postgres",
    )
    assert (
        second.inserted,
        second.updated,
        second.unchanged,
        second.deleted,
    ) == (1, 1, 0, 1)

    unchanged = load_sp500_universe(
        [
            member("AAPL", "Apple Incorporated", "320193"),
            member("NVDA", "NVIDIA Corp.", "1045810"),
        ],
        target="postgres",
    )
    assert (
        unchanged.inserted,
        unchanged.updated,
        unchanged.unchanged,
        unchanged.deleted,
    ) == (0, 0, 2, 0)


def test_postgres_adapter_rolls_back_on_delete_failure(
    postgres_test_database,
):
    load_sp500_universe(
        [
            member("AAPL", "Apple Inc.", "320193"),
            member("MSFT", "Microsoft Corp.", "789019"),
        ],
        target="postgres",
    )

    assert TEST_POSTGRES_DSN is not None
    with psycopg.connect(TEST_POSTGRES_DSN) as con:
        con.execute(
            """
            CREATE FUNCTION reject_universe_delete()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'delete rejected for transaction test';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        con.execute(
            """
            CREATE TRIGGER reject_universe_delete
            BEFORE DELETE ON sp500_universe
            FOR EACH ROW EXECUTE FUNCTION reject_universe_delete()
            """
        )

    with pytest.raises(UniverseLoadError, match="写入 postgres 失败"):
        load_sp500_universe(
            [member("AAPL", "Apple Incorporated", "320193")],
            target="postgres",
        )

    with psycopg.connect(TEST_POSTGRES_DSN) as con:
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
