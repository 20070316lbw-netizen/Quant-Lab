-- prices 表, 已复权
-- 本表在 market_data 下
-- 额外建索引 idx_daily_prices_trade_date 用于加速查询

CREATE SCHEMA IF NOT EXISTS market_data;

CREATE TABLE IF NOT EXISTS market_data.adj_daily_prices (
    trade_date   DATE NOT NULL,
    ticker       TEXT NOT NULL,

    open         NUMERIC(18, 6),
    high         NUMERIC(18, 6),
    low          NUMERIC(18, 6),
    close        NUMERIC(18, 6),

    volume       BIGINT,
    PRIMARY KEY (ticker, trade_date),

    CHECK (volume IS NULL OR volume >= 0),
    CHECK (close IS NULL OR close >= 0)
);

CREATE INDEX IF NOT EXISTS idx_daily_adj_prices_trade_date
    ON market_data.adj_daily_prices (trade_date);
