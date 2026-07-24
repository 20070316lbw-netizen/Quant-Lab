"""将数据传入数据库

目前整个项目只有 universe 有 pgsql, 不让项目暂时变得很复杂
"""


from quant_lab.config import SCHEMA_UNIVERSE
from quant_lab.connection import get_pgsql
from quant_lab.sources.universe.fetch import fetch_sp500_universe

_INSERT_SQL = """
    INSERT INTO sp500_universe (ticker, company_name, cik)
    VALUES (%s, %s, %s)
    ON CONFLICT (ticker) DO UPDATE
    SET company_name = EXCLUDED.company_name,
        cik = EXCLUDED.cik
"""



# 初始化数据库结构很重要
def init_pg_schema() -> None:
    schema_sql = SCHEMA_UNIVERSE.read_text(encoding="utf-8")

    with get_pgsql() as conn, conn.cursor() as cur:
        cur.execute(schema_sql)          # type: ignore[reportArgumentType]  # 来自可信的本地 schema 文件, 非拼接字符串

def load_universe_into_pg(universe: list) -> int:
    """把已获取的 Universe 成分股写入 PostgreSQL"""

    rows = [
        (c.ticker, c.company_name, c.cik)
        for c in universe
    ]

    if not rows:
        return 0

    with get_pgsql() as conn, conn.cursor() as cur:
        cur.executemany(_INSERT_SQL, rows)

    return len(rows)


if __name__ == "__main__":
    init_pg_schema()
    wiki_data = fetch_sp500_universe()
    count = load_universe_into_pg(wiki_data)
    print(f"写入 {count} 条记录")



    



