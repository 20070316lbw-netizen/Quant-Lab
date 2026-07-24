CREATE TABLE IF NOT EXISTS sp500_universe (
    ticker       VARCHAR(10) PRIMARY KEY,
    company_name TEXT NOT NULL,
    cik          VARCHAR(10) NOT NULL
);
