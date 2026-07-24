"""把当前 S&P 500 universe 精确同步到 DuckDB 或 PostgreSQL。

这里的"精确同步"不是普通追加:
- 新 ticker 插入;
- 公司名/CIK 变化时更新;
- 完全相同的记录不写;
- 数据库有、这次快照没有的 ticker 删除。

因此整次操作必须放在一个事务里,否则中途失败可能留下半新半旧的 universe。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import duckdb
import psycopg

from quant_lab.error import UniverseLoadError
from quant_lab.sources.universe import SP500UniverseMember
from quant_lab.storage.backend import DatabaseTarget, connect, validate_target

_DATABASE_ERRORS = (duckdb.Error, psycopg.Error)


@dataclass(frozen=True)
class UniverseLoadResult:
    """一次同步的可观察结果。

    frozen=True 表示返回后不可修改,防止日志记录前后统计数字被调用方意外改掉。
    """

    target: DatabaseTarget
    # received 是本次收到的快照总数。
    received: int
    # inserted + updated + unchanged == received;
    # deleted 单独表示旧快照中被移除的数量。
    inserted: int
    updated: int
    unchanged: int
    deleted: int


class _UniverseAdapter(Protocol):
    """DuckDB/PostgreSQL adapter 在内部必须提供的三个动作。

    Protocol 是结构化类型:
    类不需要显式继承它,只要方法长得一样,类型检查器就认为满足接口。

    业务层只通过这三个动作工作,不需要知道 ?/%s、cursor 等驱动差异。
    """

    def fetch_current(self, connection: Any) -> list[tuple[str, str, str]]: ...

    def upsert(
        self,
        connection: Any,
        rows: list[tuple[str, str, str]],
    ) -> None: ...

    def delete(self, connection: Any, tickers: list[str]) -> None: ...


class _DuckDBUniverseAdapter:
    # DuckDB 的参数占位符是 ?,不能把数据直接拼进 SQL:
    # 参数化既避免引号转义问题,也避免 SQL 注入。
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
    # psycopg 使用 %s 占位符,不是 DuckDB 的 ?。
    # SQL 的业务语义完全相同,只把真正不同的驱动细节留在 adapter 内。
    _UPSERT_SQL = """
        INSERT INTO sp500_universe (ticker, company_name, cik)
        VALUES (%s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE
        SET company_name = EXCLUDED.company_name,
            cik = EXCLUDED.cik
    """
    _DELETE_SQL = "DELETE FROM sp500_universe WHERE ticker = %s"

    def fetch_current(self, connection: Any) -> list[tuple[str, str, str]]:
        # psycopg 的批量操作通过 cursor 完成;
        # with 会在离开代码块时关闭 cursor,但不会替外层提交事务。
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


# 目标名 -> adapter 的唯一映射。
# 以后真要支持第三种数据库,至少必须在这里明确注册,不会静默回退到 PostgreSQL。
_ADAPTERS: dict[DatabaseTarget, _UniverseAdapter] = {
    "duckdb": _DuckDBUniverseAdapter(),
    "postgres": _PostgresUniverseAdapter(),
}


def _validate_snapshot(
    members: Sequence[SP500UniverseMember],
) -> list[SP500UniverseMember]:
    """在打开数据库连接之前检查会造成灾难性同步的输入问题。"""

    # Sequence 可能是 tuple 等类型;转成 list 后只遍历一次,
    # 后面的计数、构造字典和批量写入都复用同一份稳定快照。
    snapshot = list(members)

    # 精确同步会删除"本次快照里没有"的旧 ticker。
    # 所以空列表绝不能解释成"S&P 500 今天一个成员都没有",否则会清空整张表。
    if not snapshot:
        raise UniverseLoadError("sp500_universe 快照不能为空")

    # 两条相同 ticker 会让 dict 后一条覆盖前一条,掩盖上游数据错误。
    # 在接触数据库前先显式拒绝,调用方能看到真正的问题。
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
    """计算新旧快照的差异,并通过 adapter 执行最小写入。"""

    # current:数据库现在的权威状态。
    # desired:调用方希望同步完成后的状态。
    # 两边都转成 ticker -> (company_name, cik),之后比较就是普通字典/集合运算。
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

    # 集合差集/交集对应四种结果:
    # desired - current = 新成员
    # current - desired = 已退出成员
    # current & desired  = 两边都有,还需继续比较字段是否变化
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

    # 只写 inserted + updated。
    # unchanged 不执行 SQL,避免 500 条记录每次都产生无意义更新。
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

    # 删除必须和上面的 upsert 处于同一个事务:
    # 任意一步失败,外层 load_sp500_universe() 会把两步一起回滚。
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
    """把当前 S&P 500 universe 快照精确同步到一个目标数据库。

    调用方必须明确传 target,这里没有默认数据库:
    load_sp500_universe(data, target="postgres")
    load_sp500_universe(data, target="duckdb")

    这样不会因为忘传参数而误写主库,也不会自动双写造成跨库一致性问题。
    """

    # 先校验输入和 target,后连接数据库。
    # 空快照/重复 ticker/错误 target 都不会产生一次无意义连接。
    snapshot = _validate_snapshot(members)
    validated_target = validate_target(target)
    adapter = _ADAPTERS[validated_target]
    connection = None

    # 和 schema 初始化一样,用提交标记覆盖所有失败路径。
    committed = False

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
        committed = True
        return result
    except _DATABASE_ERRORS as exc:
        # 只把驱动异常翻译成项目错误。
        # 如果代码本身出现 TypeError/AttributeError,让它原样暴露,方便定位 bug。
        raise UniverseLoadError(
            f"sp500_universe 写入 {validated_target} 失败: {exc}"
        ) from exc
    finally:
        if connection is not None:
            if not committed:
                try:
                    connection.rollback()
                except _DATABASE_ERRORS:
                    # rollback 失败不能覆盖导致事务失败的第一个异常。
                    pass
            connection.close()
