from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent      # src/quant_lab
PROJECT_ROOT = PACKAGE_ROOT.parents[1]              # 仓库根目录

# TODO: 当前数据库路径写死在项目目录，后续可支持环境变量覆盖，方便部署和测试
DATABASE_PATH = PACKAGE_ROOT / "database" / "data.duckdb"
SP500_CACHE_PATH = PACKAGE_ROOT / "database" / "sp500_ticker.csv"
ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"          # 训练好的模型存这里(model.save() 的落点)


# 类变量
OHLCV_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume"]
INDEX_COLUMNS = ["date", "ticker"]

# schema 变量
SCHEMA_UNIVERSE     = PROJECT_ROOT / "db" / "schema" / "0001_sp500_universe.sql"
SCHEMA_OLCHV        = PROJECT_ROOT / "db" / "schema" / "0002_sp500_prices.sql"
SCHEMA_OLCHV_ADJ    = PROJECT_ROOT / "db" / "schema" / "0003_sp500_adj_prices.sql"

# 环境变量
# 每个变量都是 os.environ.get(..., 默认值)
load_dotenv()  # 读根目录的 .env 文件,把里面每一行 KEY=VALUE 写进 os.environ
DB_NAME     : str           = os.environ.get("DB_NAME", "quant_lab")
DB_HOST     : str | None    = os.environ.get("DB_HOST")                 # 不设就走本地 Unix socket
DB_PORT     : int           = int(os.environ.get("DB_PORT", "5432"))
DB_USER     : str | None    = os.environ.get("DB_USER")                 # 不设就用当前系统用户(trust 认证)
DB_PASSWORD : str | None    = os.environ.get("DB_PASSWORD")


"""快捷留空:
要跑测试库、或者部署到服务器上连另一个数据库,只需要在跑代码前设一下
代码本身一行不用改:

```bash
DB_NAME=quant_db_test python src/sql/ingest/load_securities.py
```
"""

"""写给以后的自己
为什么 DB_HOST 默认是 None,而不是 "localhost"

本地不设 host,psycopg 连的是 Unix domain socket,不是 TCP 的 localhost
这两者是不同的连接方式:
Unix socket 是同一台机器上进程间通过文件系统的一个特殊文件通信,不走网络协议栈
比 TCP 连 127.0.0.1 更快,也不需要端口
Homebrew 装的 Postgres 默认就监听在 Unix socket 上
这也是为什么平时 psql quant_db 不用指定任何 host/port 就能连上

所以这段代码的意思是:"没告诉我 host,就默认你在本机开发,直接走 socket";
只有当你连远程数据库(比如以后上了云)时才会设 DB_HOST,
这时才会真正用上下面的 TCP 连接参数

为什么 user/password 也是可选的:
跟之前搞清楚的一样,本地 Homebrew Postgres 走 trust 认证,
直接对应你的系统用户名(liu),不需要密码
所以这两个字段默认 None,只有连需要认证的远程库时才会填
"""