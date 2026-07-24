CREATE TABLE IF NOT EXISTS prices (
    date   DATE,
    ticker VARCHAR,
    open   DOUBLE PRECISION,
    high   DOUBLE PRECISION,
    low    DOUBLE PRECISION,
    close  DOUBLE PRECISION,
    volume BIGINT,
    PRIMARY KEY (date, ticker)
);
