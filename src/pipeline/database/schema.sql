-- prices 表
CREATE TABLE IF NOT EXISTS prices(
    date DATE,
    ticker VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    PRIMARY KEY (date, ticker)
)

