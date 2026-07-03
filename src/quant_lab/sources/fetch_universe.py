"""标的池(universe)数据源: 从 Wikipedia 抓取 S&P 500 成分股列表"""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests
from loguru import logger

from quant_lab.sources.base import DataSource
from quant_lab.config import SP500_CACHE_PATH

_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 校验用: SEC 官方全量 ticker -> CIK 映射表, 只在 validate_cik_against_sec 里用到,
# 不参与主流程(主流程走 load_cached_universe, 直接用 Wikipedia 自带的 cik 列)
_SEC_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
_SEC_HEADERS = {"User-Agent": "liu 20070316lbw@gmail.com"}      # EDGAR 要求带可识别的 User-Agent

class SP500Universe(DataSource):
    """S&P 500 成分股列表。

    Returns 列:
        ticker   (str): 股票代码, 已规范化('.' -> '-' 以兼容 yfinance, 如 BRK.B -> BRK-B)。
        security (str): 公司名称。
        cik      (str): SEC 的 10 位零填充 CIK, 基本面抓取要用它定位公司。
    """

    def fetch(self) -> pd.DataFrame:
        logger.info("正在抓取 S&P 500 成分股列表 ...")
        # TODO: 增加 requests.RequestException 捕获并统一转换为项目内部异常类型
        resp = requests.get(_WIKI_URL, headers = {"User-Agent": _BROWSER_UA}, timeout = 30)
        resp.raise_for_status()

        # TODO: Wikipedia 页面结构变更后 [0] 可能不再是成分股表，建议增加表结构校验
        table = pd.read_html(StringIO(resp.text))[0]

        # TODO: 当前假设 Symbol/Security/CIK 三列始终存在，后续应校验列名后再重命名
        df = table.rename(
            columns = {"Symbol" : "ticker",
                       "Security" : "security",
                       "CIK" : "cik"}
        )[["ticker", "security", "cik"]].copy()

        # 规范化: CIK 左补零到 10 位(EDGAR 接口只吃 10 位)
        # TODO: 若 Wikipedia 出现缺失值，astype(str) 可能产生 '<NA>' 字符串，需要单独处理
        df["cik"] = df["cik"].astype("Int64").astype(str).str.zfill(10)
        df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)

        # TODO: 考虑记录抓取数量和样本范围，便于后续排查 universe 变化
        return df


def load_cached_universe() -> pd.DataFrame:
    """读取 build_db.py 缓存下来的 S&P 500 成分股列表(sp500_ticker.csv)。

    显式把 cik 列按字符串读取, 并重新补零到 10 位——CSV 是纯文本格式,
    不保留 DataFrame 原始的 dtype, pandas 默认读取时会把这种全数字的列
    自动推断成 int, 导致补零丢失(0000066740 会变成 66740)。
    """
    if not SP500_CACHE_PATH.exists():
        raise FileNotFoundError(
            f"{SP500_CACHE_PATH} 不存在, 请先跑一次 build_db.py 生成缓存"
        )

    df = pd.read_csv(SP500_CACHE_PATH, dtype={"cik": str})
    df["cik"] = df["cik"].str.zfill(10)
    return df


def validate_cik_against_sec(universe: pd.DataFrame) -> set[str]:
    """拿 SEC 官方注册库交叉校验 universe 里的 CIK 是否真实存在。

    不是主流程的一部分, 主流程(edgar.py)一直信任 Wikipedia 自带的 cik 列。
    这个函数是数据可疑时手动抽查用的: 万一 Wikipedia 某一行被人编辑错了、
    或者哪个 CIK 看起来不像正常范围, 拿它跑一次交叉核对。

    Returns:
        SEC 官方注册库里查不到的 CIK 集合。空集合说明全部通过校验。
    """
    logger.info("正在拉取 SEC 官方 CIK 注册库做交叉校验 ...")
    # TODO: 增加 requests.RequestException 捕获并统一转换为项目内部异常类型
    resp = requests.get(_SEC_CIK_URL, headers=_SEC_HEADERS, timeout=30)
    resp.raise_for_status()

    sec_valid_ciks = {str(v["cik_str"]).zfill(10) for v in resp.json().values()}
    wiki_ciks = set(universe["cik"])

    invalid = wiki_ciks - sec_valid_ciks
    if invalid:
        logger.warning(f"以下 CIK 在 SEC 官方注册库里查不到: {sorted(invalid)}")
    else:
        logger.success(f"校验通过: {len(wiki_ciks)} 个 CIK 全部能在 SEC 官方注册库里查到")

    return invalid


if __name__ == "__main__":
    S = SP500Universe()
    df = S.fetch()
    # TODO: 调试代码，后续改成 logger 或单元测试
    print(df)


