import duckdb
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent      # src/pipeline
PROJECT_ROOT = PACKAGE_ROOT.parents[1]              # 仓库根目录

DATABASE_PATH = PACKAGE_ROOT / "database" / "data.duckdb"
SCHEMA = PACKAGE_ROOT / "database" / "schema.sql"
SP500_CACHE_PATH = PACKAGE_ROOT / "database" / "sp500_ticker.csv"

TEMP_DIR = PROJECT_ROOT / "aapl.csv"

def get_duckdb() -> duckdb.DuckDBPyConnection:
    """返回一个 DuckDB 连接。

    调用方负责关闭, 推荐用 with 语法自动关闭:

        with get_connection() as con:
            ...
    """
    return duckdb.connect(str(DATABASE_PATH))