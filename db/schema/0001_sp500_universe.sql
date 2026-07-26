-- sp500_universe 股票池表
-- 本表在 universe 下
CREATE SCHEMA IF NOT EXISTS universe;

CREATE TABLE IF NOT EXISTS universe.sp500_universe (
    -- ticker 是当前快照中的稳定业务键;重复同步时由它判断插入还是更新。
    ticker       VARCHAR(10) PRIMARY KEY,
    company_name TEXT NOT NULL,
    -- CIK 必须保留前导零,所以使用字符串而不是 INTEGER。
    cik          VARCHAR(10) NOT NULL
);
