"""标的抓取"""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator

from quant_lab.config import SP500_CACHE_PATH
from quant_lab.error import WikiFetchError

_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_SEC_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
_SEC_HEADERS = {"User-Agent": "liu 20070316lbw@gmail.com"}

# 这不是为了声称 S&P 500 永远刚好 500 行:
# 同股不同类别会让实际行数略多于 500。
# 范围检查的目的只是拦住"网页结构变了,却碰巧解析出几行合法数据"这种危险情况;
# 因为下游是精确同步,残缺列表会把缺失 ticker 当成退出成员删除。
_MIN_EXPECTED_UNIVERSE_SIZE = 400
_MAX_EXPECTED_UNIVERSE_SIZE = 600


class SP500UniverseMember(BaseModel):
    """校验通过的一条 S&P 500 成分股记录, 校验通过才允许入库。"""

    ticker      : str = Field(min_length=1, max_length=10)
    company_name: str = Field(min_length=1)
    cik         : str = Field(
        pattern     = r"^\d{10}$",
        description ="SEC CIK, 固定 10 位数字, 不足的时候补 0",
    )
    # ^\d{10}$：^ $ 锁定首尾避免部分匹配混过, \d{10} 要求恰好 10 位数字


    @field_validator("cik", mode="before")
    @classmethod
    def _pad_cik(cls, v: object) -> object:
        """类型转换前补 0, 保住前导零。"""
        if isinstance(v, int):
            return str(v).zfill(10)

        if isinstance(v, str) and v.isdigit():
            """
            isdigit() 是 Python 字符串的方法，用来判断一个字符串是否全部由“数字字符”组成

            ```python
            "12345".isdigit()      # True
            "0000123456".isdigit() # True
            "12A45".isdigit()      # False
            "12.45".isdigit()      # False
            "-123".isdigit()       # False
            "".isdigit()           # False
            ```
            """
            return v.zfill(10)

        return v


    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker(cls, v: object) -> object:
        """统一使用 yfinance 接受的 ticker 表示。"""
        if isinstance(v, str):
            return v.strip().upper().replace(".", "-")
        return v


    @field_validator("cik")
    @classmethod
    def _validate_cik_format(cls, v: str) -> str:
        """确保 CIK 是 10 位数字。"""
        if not (v.isdigit() and len(v) == 10):
            raise ValueError("CIK 必须是 10 位数字")

        return v


    @field_validator("company_name")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        """
        strip() 是字符串方法, 用来删除字符串首尾的空白字符
        例如空格、换行、Tab;中间的内容不动

        ```python
        "  AAPL  ".strip()      # "AAPL"
        "\n 123 \t".strip()     # "123"
        "Apple Inc".strip()     # "Apple Inc"
        ```
        """
        normalized = v.strip()
        if not normalized:
            raise ValueError("公司名称不能为空")
        return normalized


def fetch_sp500_universe() -> list[SP500UniverseMember]:
    """从维基百科抓取当前 S&P 500 成分股列表, 逐条校验后返回。

    Returns:
        list[SP500UniverseMember]: 校验通过的成分股列表。

    Raises:
        WikiFetchError: 请求失败、表格解析失败, 或解析出的列表为空。
    """
    try:
        resp = requests.get(
            _WIKI_URL, 
            headers = {"User-Agent": _BROWSER_UA},
            timeout = 10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise WikiFetchError(f"维基百科请求失败: -{exc}") from exc

    try:
        # StringIO 包一层：直接传 resp.text 有时会被 lxml 当成文件名/URL 处理
        # converters={"CIK": str}：强制该列按字符串解析, 否则前导零会被当整数吃掉
        table = pd.read_html(StringIO(resp.text), converters={"CIK": str})[0]
    except (ValueError, IndexError) as exc:
        raise WikiFetchError(f"页面解析失败, 可能是页面结构改变: {exc}") from exc

    # 对内容进行检查
    # set(table.columns) 是把 DataFrame 实际有的列名转成一个集合
    # 集合减法 A - B 的意思是"在 A 里、但不在 B 里的元素"
    required_columns = {"Symbol", "Security", "CIK"}
    missing_columns = required_columns - set(table.columns)
    if missing_columns:
        raise WikiFetchError(
            f"页面缺少必要字段: {sorted(missing_columns)}"     
            # `sorted()`: Python 内置函数,
            # 输入任何可迭代对象(list、set、dict 的 keys 等),返回一个排好序的新 list,原对象不变
            # missing_columns 和后面的 invalid 都是 set(集合)集合本身是无序的,
            # 直接塞进 f-string 打印出来,每次运行元素顺序可能不一样,报错/日志信息不稳定,
            # 不方便人看、也不方便你复制去对比
            # sorted(missing_columns) 把它转成按字母顺序排好的 list,保证日志每次长得一样,方便读。
        )

    universe: list[SP500UniverseMember] = []

    for row_number, (_, row) in enumerate(table.iterrows()):
        """
        .iterrows() 会把每一行拿出来,返回 (索引, 该行数据) 这样的元组,
        外面再套一层 enumerate(...),会变成 (0, (0, <Series>)), (1, (1, <Series>))……
        用 _ 表示"我不关心索引值,只要行内容",
        row 就是这一行的数据(可以像字典一样用 row["Symbol"] 取值)

        所以 for row_number, (_, row) in enumerate(...) 里:
        row_number 来自 enumerate,是"这是第几次循环",从 0 开始连续计数
        (_, row) 是在拆 iterrows() 给的那个元组,_ 是 DataFrame 原始的行索引(不要了),
        row 才是真正的这一行数据

        为什么不直接用 iterrows() 自带的索引,非要多套一层 enumerate?
        因为 DataFrame 的索引不一定是连续的整数——比如如果表格在此之前被筛选/去重过,
        索引可能是 0, 1, 5, 8... 这种跳着的
        用 enumerate 保证报错信息里的"第几行"永远是人能直接理解的、从 0 连续数下来的行号
        """
        try:
            universe.append(
                SP500UniverseMember(
                    ticker=row["Symbol"],
                    company_name=row["Security"],
                    cik=row["CIK"]
                )
            )

        except ValidationError as exc:
            # 不能像普通 ETL 那样"坏一行就跳过":
            # 下游会把整份列表视为权威快照,跳过一行等价于宣告该 ticker 已退出指数。
            # 所以这里采取 fail closed——任意一行非法,整次抓取失败且不入库。
            raise WikiFetchError(
                f"第 {row_number} 行校验失败，拒绝使用不完整快照: "
                f"{row.to_dict()}"
            ) from exc


    if not universe:
        raise WikiFetchError("解析出的成分股列表为空, 页面结构可能变化")

    """
    空列表保护只能拦住 0 行;如果页面变化后错误解析出 1~20 行,仍然很危险。
    再做一次宽松的数量合理性检查,避免小块残缺数据清掉大部分数据库记录。
    """
    if not (
        _MIN_EXPECTED_UNIVERSE_SIZE
        <= len(universe)
        <= _MAX_EXPECTED_UNIVERSE_SIZE
    ):
        raise WikiFetchError(
            f"成分股数量异常: {len(universe)},"
            f"预期范围 {_MIN_EXPECTED_UNIVERSE_SIZE}"
            f"~{_MAX_EXPECTED_UNIVERSE_SIZE}"
        )

    logger.info(f"成功抓取并且校验 {len(universe)} 条 S&P 成分股")

    return universe


def load_cached_universe() -> pd.DataFrame:
    """读取本地 universe CSV, 同时保留 CIK 的前导零。"""
    if not SP500_CACHE_PATH.exists():
        raise FileNotFoundError(
            f"{SP500_CACHE_PATH} 不存在, 请先运行 prices build 生成缓存"
        )

    universe = pd.read_csv(SP500_CACHE_PATH, dtype={"cik": str})
    """
    dtype={"cik": str} 只是告诉 pandas"这一列按字符串读,别转成 int"
    但字符串本身长什么样,取决于 CSV 文件里存的是什么
    如果当初写 CSV 的时候不小心把补零漏掉了(比如某个环节又把它转成 int 存进去了,前导零丢了)
    读回来的字符串就是 "320193" 而不是 "0000320193"
    .str.zfill(10) 是 pandas 对整列做字符串补零的向量化操作,
    相当于对每一行都跑一遍前面 pydantic 里 _pad_cik 的逻辑,
    确保不管 CSV 里存的是什么样子,读出来一定是标准 10 位
    这是一种"不信任存储介质,读的时候再兜底一次"的防御写法。
    """
    universe["cik"] = universe["cik"].str.zfill(10)
    return universe


def validate_cik_against_sec(universe: pd.DataFrame) -> set[str]:
    """用 SEC 官方注册库手动交叉检查 universe 中的 CIK。"""
    logger.info("正在拉取 SEC 官方 CIK 注册库做交叉校验 ...")
    try:
        response = requests.get(
            _SEC_CIK_URL,
            headers=_SEC_HEADERS,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WikiFetchError(f"SEC CIK 注册库请求失败: {exc}") from exc

    sec_valid_ciks = {
        str(value["cik_str"]).zfill(10)
        for value in response.json().values()
    }
    """response.json() 返回的结构大概长这样:

        ```python
    {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, 
    ```
    外层的 "0", "1" 这些 key 没用,所以用 .values() 只取里面的每一条记录,
    再从每条记录里挑出 cik_str,转字符串、补零,塞进一个 set 里去重
    """
    
    wiki_ciks = set(universe["cik"])
    invalid = wiki_ciks - sec_valid_ciks

    if invalid:
        logger.warning(f"以下 CIK 在 SEC 官方注册库里查不到: {sorted(invalid)}")
    else:
        logger.success(f"校验通过: {len(wiki_ciks)} 个 CIK 全部能查到")
    return invalid
