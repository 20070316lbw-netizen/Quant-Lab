from __future__ import annotations

from quant_lab.connection import get_pgsql

with get_pgsql() as conn, conn.cursor() as cur:
    detail = cur.execute("""
        SELECT COUNT(DISTINCT trade_date)
        FROM market_data.daily_prices;
    """).fetchone()
    print(detail)