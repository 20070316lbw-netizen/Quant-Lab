CREATE TABLE sp500_constituents (
    ticker          VARCHAR(10),
    company_name    TEXT NOT NULL,
    cik             VARCHAR(10) NOT NULL,
    PRIMARY KEY (ticker)
);