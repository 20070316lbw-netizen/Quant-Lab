-- prices 表, 未复权
-- 本表在 market_data 下
-- 额外建索引 idx_daily_prices_trade_date 用于加速查询

CREATE SCHEMA IF NOT EXISTS market_data;

CREATE TABLE IF NOT EXISTS market_data.daily_prices (
    trade_date      DATE NOT NULL,
    ticker          TEXT NOT NULL,

    open            DOUBLE PRECISION,
    high            DOUBLE PRECISION,
    low             DOUBLE PRECISION,
    close           DOUBLE PRECISION,
    adj_close       DOUBLE PRECISION,

    volume          BIGINT,
    dividends       DOUBLE PRECISION NOT NULL DEFAULT 0,
    stock_splits    DOUBLE PRECISION NOT NULL DEFAULT 0,

    PRIMARY KEY (ticker, trade_date),
    CHECK (volume IS NULL OR volume >= 0),
    CHECK (close IS NULL OR close >= 0),
    CHECK (adj_close IS NULL OR adj_close >= 0)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_trade_date
    ON market_data.daily_prices (trade_date);
