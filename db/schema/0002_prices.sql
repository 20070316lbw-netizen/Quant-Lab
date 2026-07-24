-- prices 的结构也必须由 schema 文件统一管理。
-- Python 入库代码只写数据,不再维护第二份 CREATE TABLE。
CREATE TABLE IF NOT EXISTS prices (
    date   DATE,
    ticker VARCHAR,
    -- DOUBLE PRECISION 是 PostgreSQL/DuckDB 都接受的写法。
    open   DOUBLE PRECISION,
    high   DOUBLE PRECISION,
    low    DOUBLE PRECISION,
    close  DOUBLE PRECISION,
    volume BIGINT,
    -- 同一 ticker 在同一天只能有一条价格记录,重复运行 pipeline 时据此 upsert。
    PRIMARY KEY (date, ticker)
);
