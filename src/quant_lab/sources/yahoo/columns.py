"""Yahoo 日频价格在抓取层和入库层之间共享的字段契约。"""

from __future__ import annotations

# 未复权表保留 Yahoo 返回的 adj_close 和公司行动。
RAW_PRICE_COLUMNS = (
    "trade_date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "dividends",
    "stock_splits",
)

# 复权表中的 OHLC 已经全部经过拆股、分红调整，不再单独保存 adj_close。
ADJ_PRICE_COLUMNS = (
    "trade_date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "volume",
)