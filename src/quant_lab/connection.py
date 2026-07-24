"""数据库连接入口

目前已有两个数据库可使用:
1. DuckDB
2. PostgreSQL

调用实例

```python
with get_duckdb() as conn:
    conn.execute("""""")
```

```python
with get_pgsql() as conn, conn.cursor() as cur:
    cur.execute(schema_sql)  # type: ignore[reportArgumentType]  # 来自可信的本地 schema 文件, 非拼接字符串
"""

from typing import Any

import duckdb
import psycopg

from quant_lab.config import (
    DATABASE_PATH,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
)


def get_duckdb(*, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """返回一个 DuckDB 连接。

    调用方负责关闭, 推荐用 with 语法自动关闭:

    TODO:
        后续可统一从这里注入 DuckDB 配置(PRAGMA、线程数、只读模式等)
    """
    # TODO: DATABASE_PATH 对应目录不存在时会报错，后续可在这里自动创建目录
    return duckdb.connect(str(DATABASE_PATH), read_only=read_only)



def get_pgsql(*, read_only: bool = False) -> psycopg.Connection:
    """返回一个 pgsql 连接
    存在的意义就是:把"怎么连"这件事集中到一个地方,其他代码只管调用它,不管细节
    函数与 `config.py` 里那几行互相配合
    """



    """
    问题: 为什么以下代码会被 pylance 报错
    ```python
    from pathlib import Path

    from quant_lab.config import SCHEMA_UNIVERSE
    from quant_lab.connection import get_duckdb, get_pgsql


    # 初始化数据库结构很重要
    def init_pg_schema() -> None:
        schema_sql = SCHEMA_UNIVERSE.read_text(encoding="utf-8")

        with get_pgsql() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
    ```
    这里是强度到 "值得翻源码" 的程度
    psycopg[binary] 有两个重载方式:

    重载 1 要的是 LiteralString,不是普通 str
    LiteralString 是个很特殊的静态类型——只有"写死在代码里的字符串字面量"(比如直接敲 "select 1")才算数
    schema_sql 虽然内容是纯文本,但它是函数调用的返回值(.read_text()),在类型检查器眼里,
    只要经过一次变量赋值/函数调用,就"降级"成普通 str 了,不再是 LiteralString
    所以配不上重载 1
    额外说一下, 这个限制的用意是:
    果你不传 params(参数化查询),psycopg 希望你的 SQL 是写死在代码里的字面量,
    而不是运行时拼出来的字符串,因为运行时字符串"理论上"可能是拼了不可信输入进去、有 SQL 注入风险
    你这里的 schema_sql 虽然是运行时读出来的,但内容来自你自己项目里的可信 .sql 文件,
    完全没有注入风险——只是类型检查器没法理解"这个字符串虽然不是字面量,但来源可信",
    它只能死板地按"是不是字面量"判断。

    重载 2 要的是 Template。这是 Python 3.14 才有的新语法(PEP 750,t"..." 模板字符串),
    让你能写 t"SELECT * FROM t WHERE id = {id}" 这种,
    库会自动把 {id} 安全地转成参数化查询,不用你另外传 params。
    我去看了 psycopg 的 _compat.py,发现在 3.14 以下的环境里,
    Template 只是一个凑数的占位类(__new__ 直接返回一个空实例,压根不能真正用),
    而你项目跑的是 Python 3.12,这条重载路径本来就用不上
    schema_sql 当然也不是这个类型,所以也配不上重载 2。

    Pylance 显示"重载 2 是最接近的匹配项",只是它在两个都不匹配的情况下,
    挑一个报错信息"看起来更少"的重载来给你展示,不代表真的接近,你可以不用太纠结这句话本身。

    此问题已修改:
    怎么处理
    加一行 # type: ignore 忽略掉,最省事,而且你现在确实理解了原因,加注释说明一下即可:
    ```python
    cur.execute(schema_sql)  # type: ignore[reportCallIssue]  # 来自可信的本地 schema 文件, 非拼接字符串
    ```
    """
    

    """
    留给未来的自己:
    要建一条数据库连接,理论上需要五样东西:库名、主机地址、端口、用户名、密码
    本地开发时,实际只需要库名——其他四样 Postgres 会用默认规则帮你填好
    (本地 socket、5432 端口、当前系统用户、免密码)

    config.py 里那几行做的就是"把这五样东西准备好,
    能拿到环境变量就用环境变量,拿不到就用本地默认值":
    DB_NAME: str = os.environ.get("DB_NAME", "quant_lab")
    DB_HOST: str | None = os.environ.get("DB_HOST")
    注意 DB_HOST 没有第二个参数(默认值),这是故意的——它默认就是 None,
    代表"不知道 host 就是本地"

    """

    # kwargs 是个普通字典,现在里面只有一项:{"dbname": "quant_db"}
    # 是本地开发时,最终真正会传给 psycopg.connect() 的全部内容
    # kwargs: dict[str, str | int] = {"dbname": DB_NAME}    <--- 这是之前的写法
    kwargs: dict[str, Any] = {"dbname": DB_NAME}          # <--- 先用这个替代一下

    # 接下来两个 if:
    # 只有当你真的设置了 DB_HOST 这个环境变量,我才往字典里加 host 和 port
    # 如果无脑写 kwargs["host"] = DB_HOST,而 DB_HOST 是 None,
    # 那 psycopg.connect() 收到的就是 host=None——这会被解释成
    # "你明确要求走 TCP 连接,只是没告诉我地址",
    # 这时候它就不会走本地默认的 Unix socket 了,反而可能连接失败
    # 所以用 if 守一道,保证"没设就完全不提这件事"
    # 让 psycopg 用它自己的默认逻辑(本地 socket)
    # DB_USER、DB_PASSWORD 同理
    if DB_HOST:
        kwargs["host"] = DB_HOST
        kwargs["port"] = DB_PORT

    if DB_USER:
        kwargs["user"] = DB_USER

    if DB_PASSWORD:
        kwargs["password"] = DB_PASSWORD

    # kwargs 是个字典,比如 {"dbname": "quant_lab"}
    # 前面加两个星号 **,意思是"把这个字典拆开,变成一个个关键字参数传进去"
    # 也就是说:
    # psycopg.connect(**{"dbname": "quant_lab"})
    # 等价于
    # psycopg.connect(dbname="quant_lab")

    # 如果 kwargs 里有更多项,比如加了 host/port,效果就是
    # psycopg.connect(**{"dbname": "quant_db", "host": "1.2.3.4", "port": 5432})
    # 等价于
    # psycopg.connect(dbname="quant_db", host="1.2.3.4", port=5432)
    # 这就是为什么要先攒一个字典再展开
    # 因为参数个数是不确定的(有时候 2 个,有时候 5 个)
    # 用字典 + ** 就能优雅地应对"参数数量可变"这件事,
    # 不用写一堆 if...elif... 去处理每种参数组合。
    conn = psycopg.connect(**kwargs)        # 先建连接
    """
    这里有一个很经典的坑, 对应上面的
    kwargs: dict[str, str | int] = {"dbname": DB_NAME}
    
    用 ** 展开一个"普通字典"(不是下面要讲的 TypedDict)
    类型检查器没法知道你这个字典里实际装的是哪几个 key

    所以它只能保守假设:"这个字典可能匹配 connect() 里任何一个关键字参数"
    于是它把 str | int 挨个去对 connect() 签名里的每一个参数类型做检查:

    autocommit: bool ← str | int 塞不进 bool → 报错
    prepare_threshold: int | None ← str | int 里的 str 塞不进 int | None → 报错
    context: AdaptContext | None ← 完全不兼容 → 报错
    conninfo: str ← str | int 里的 int 塞不进 str → 报错
    类型检查器在"疑罪从有"——因为它没法证明你的字典里不会出现这些 key,
    只好把每个可能性都检查一遍,然后全部报错
    运行时其实完全没问题,因为你实际塞进去的只有 dbname/host/port/user/password 
    这几个 key,connect() 认识它们、类型也对得上

    高级解决方法:
    用 TypedDict 精确描述这个字典长什么样

    ```python
    from typing import TypedDict

    class ConnKwargs(TypedDict, total=False):
        dbname: str
        host: str
        port: int
        user: str
        password: str

    kwargs: ConnKwargs = {"dbname": DB_NAME}
    ```
    """

    # 这个和函数签名里的 * 打配合
    conn.read_only = read_only
    # 设成 True 之后,psycopg3 会在这条连接开始事务时,
    # 自动帮你在数据库层面执行 SET TRANSACTION READ ONLY。
    # 重点是这不是 Python 代码层面拦你,是数据库自己收到写操作会直接拒绝
    # 所以哪怕你脚本里手滑写了 UPDATE,数据不会真的被改,数据库会直接报
    # 这也是为什么建议所有"只是查询/跑报表"的脚本都传 read_only=True:
    # 给自己上把锁,防止手误

    return conn 


