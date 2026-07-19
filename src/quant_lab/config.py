import duckdb
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent      # src/quant_lab
PROJECT_ROOT = PACKAGE_ROOT.parents[1]              # 仓库根目录

# TODO: 当前数据库路径写死在项目目录，后续可支持环境变量覆盖，方便部署和测试
DATABASE_PATH = PACKAGE_ROOT / "database" / "data.duckdb"
SCHEMA = PACKAGE_ROOT / "database" / "schema.sql"
SP500_CACHE_PATH = PACKAGE_ROOT / "database" / "sp500_ticker.csv"
ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"          # 训练好的模型存这里(model.save() 的落点)


# 类变量
OHLCV_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume"]
INDEX_COLUMNS = ["date", "ticker"]

# TODO: 变量名叫 TEMP_DIR，但实际是文件路径，建议后续改名为 TEMP_FILE 或 TEMP_CSV_PATH
TEMP_DIR = PROJECT_ROOT / "aapl.csv"


def get_duckdb(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """返回一个 DuckDB 连接。

    调用方负责关闭, 推荐用 with 语法自动关闭:

    TODO:
        后续可统一从这里注入 DuckDB 配置(PRAGMA、线程数、只读模式等)
    """
    # TODO: DATABASE_PATH 对应目录不存在时会报错，后续可在这里自动创建目录
    return duckdb.connect(str(DATABASE_PATH), read_only=read_only)
