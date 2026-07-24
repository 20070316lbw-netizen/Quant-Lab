from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from quant_lab.error import UniverseLoadError
from quant_lab.sources.universe import SP500UniverseMember
from quant_lab.storage.backend import DatabaseTarget, connect, validate_target


@dataclass(frozen=True)
class UniverseLoadResult:
    target: DatabaseTarget
    received: int
    inserted: int
    updated: int
    unchanged: int
    deleted: int


class _UniverseAdapter(Protocol):
    def fetch_current(self, connection: Any) -> list[tuple[str, str, str]]: ...

    def upsert(
        self,
        connection: Any,
        rows: list[tuple[str, str, str]],
    ) -> None: ...

    def delete(self, connection: Any, tickers: list[str]) -> None: ...


class _DuckDBUniverseAdapter:
    _UPSERT_SQL = """
        INSERT INTO sp500_universe (ticker, company_name, cik)
        VALUES (?, ?, ?)
        ON CONFLICT (ticker) DO UPDATE
        SET company_name = EXCLUDED.company_name,
            cik = EXCLUDED.cik
    """
    _DELETE_SQL = "DELETE FROM sp500_universe WHERE ticker = ?"

    def fetch_current(self, connection: Any) -> list[tuple[str, str, str]]:
        return connection.execute(
            "SELECT ticker, company_name, cik FROM sp500_universe"
        ).fetchall()

    def upsert(
        self,
        connection: Any,
        rows: list[tuple[str, str, str]],
    ) -> None:
        if rows:
            connection.executemany(self._UPSERT_SQL, rows)

    def delete(self, connection: Any, tickers: list[str]) -> None:
        if tickers:
            connection.executemany(
                self._DELETE_SQL,
                [(ticker,) for ticker in tickers],
            )


class _PostgresUniverseAdapter:
    _UPSERT_SQL = """
        INSERT INTO sp500_universe (ticker, company_name, cik)
        VALUES (%s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE
        SET company_name = EXCLUDED.company_name,
            cik = EXCLUDED.cik
    """
    _DELETE_SQL = "DELETE FROM sp500_universe WHERE ticker = %s"

    def fetch_current(self, connection: Any) -> list[tuple[str, str, str]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT ticker, company_name, cik FROM sp500_universe"
            )
            return cursor.fetchall()

    def upsert(
        self,
        connection: Any,
        rows: list[tuple[str, str, str]],
    ) -> None:
        if rows:
            with connection.cursor() as cursor:
                cursor.executemany(self._UPSERT_SQL, rows)

    def delete(self, connection: Any, tickers: list[str]) -> None:
        if tickers:
            with connection.cursor() as cursor:
                cursor.executemany(
                    self._DELETE_SQL,
                    [(ticker,) for ticker in tickers],
                )


_ADAPTERS: dict[DatabaseTarget, _UniverseAdapter] = {
    "duckdb": _DuckDBUniverseAdapter(),
    "postgres": _PostgresUniverseAdapter(),
}


def _validate_snapshot(
    members: Sequence[SP500UniverseMember],
) -> list[SP500UniverseMember]:
    snapshot = list(members)
    if not snapshot:
        raise UniverseLoadError("sp500_universe 快照不能为空")

    seen: set[str] = set()
    duplicates: set[str] = set()
    for universe_member in snapshot:
        if universe_member.ticker in seen:
            duplicates.add(universe_member.ticker)
        seen.add(universe_member.ticker)

    if duplicates:
        raise UniverseLoadError(
            f"sp500_universe 存在重复 ticker: {sorted(duplicates)}"
        )
    return snapshot


def _synchronize(
    connection: Any,
    adapter: _UniverseAdapter,
    members: list[SP500UniverseMember],
    target: DatabaseTarget,
) -> UniverseLoadResult:
    current = {
        ticker: (company_name, cik)
        for ticker, company_name, cik in adapter.fetch_current(connection)
    }
    desired = {
        universe_member.ticker: (
            universe_member.company_name,
            universe_member.cik,
        )
        for universe_member in members
    }

    current_tickers = set(current)
    desired_tickers = set(desired)
    inserted_tickers = desired_tickers - current_tickers
    deleted_tickers = current_tickers - desired_tickers
    shared_tickers = current_tickers & desired_tickers
    updated_tickers = {
        ticker
        for ticker in shared_tickers
        if current[ticker] != desired[ticker]
    }
    unchanged_tickers = shared_tickers - updated_tickers
    changed_tickers = inserted_tickers | updated_tickers

    adapter.upsert(
        connection,
        [
            (
                universe_member.ticker,
                universe_member.company_name,
                universe_member.cik,
            )
            for universe_member in members
            if universe_member.ticker in changed_tickers
        ],
    )
    adapter.delete(connection, sorted(deleted_tickers))

    return UniverseLoadResult(
        target=target,
        received=len(members),
        inserted=len(inserted_tickers),
        updated=len(updated_tickers),
        unchanged=len(unchanged_tickers),
        deleted=len(deleted_tickers),
    )


def load_sp500_universe(
    members: Sequence[SP500UniverseMember],
    *,
    target: DatabaseTarget,
) -> UniverseLoadResult:
    """把当前 S&P 500 universe 快照精确同步到一个目标数据库。"""
    snapshot = _validate_snapshot(members)
    validated_target = validate_target(target)
    adapter = _ADAPTERS[validated_target]
    connection = None

    try:
        connection = connect(validated_target)
        connection.execute("BEGIN")
        result = _synchronize(
            connection,
            adapter,
            snapshot,
            validated_target,
        )
        connection.commit()
        return result
    except UniverseLoadError:
        raise
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise UniverseLoadError(
            f"sp500_universe 写入 {validated_target} 失败: {exc}"
        ) from exc
    finally:
        if connection is not None:
            connection.close()
