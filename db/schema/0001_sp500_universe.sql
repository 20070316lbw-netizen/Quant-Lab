-- PostgreSQL 和 DuckDB 共用这份 DDL。
-- 因此只使用两边都支持的基础类型与约束,不要在这里加入单库专属语法。
CREATE TABLE IF NOT EXISTS sp500_universe (
    -- ticker 是当前快照中的稳定业务键;重复同步时由它判断插入还是更新。
    ticker       VARCHAR(10) PRIMARY KEY,
    company_name TEXT NOT NULL,
    -- CIK 必须保留前导零,所以使用字符串而不是 INTEGER。
    cik          VARCHAR(10) NOT NULL
);
