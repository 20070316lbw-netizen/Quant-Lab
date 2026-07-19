"""EDGAR 基本面数据源: 按 point-in-time 方式抓取公司财务字段(book equity / shares outstanding)"""

from __future__ import annotations

from loguru import logger

from quant_lab.sources.base import DataSource
from quant_lab.sources.fetch_universe import load_cached_universe


# ---------------- 定义全局常量 ---------------------
HEADERS = {"User-Agent": "liu 20070316lbw@gmail.com"}       # EDGAR 要求所有接口(含 companyconcept)带 User-Agent
URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
CONCEPT = "StockholdersEquity"      # book equity, FF3 第一个要接入的字段, 先只跑通这一个


class FetchEdgar(DataSource):
    """整个抓取 EDGAR 的大类, 继承 base.py 下的 Datasource 类。

    CIK 直接复用 fetch_universe.py 缓存里 Wikipedia 自带的那一列,
    不再单独抓 SEC 的 company_tickers.json 做 ticker -> CIK 映射:
    两个数据源对同一家公司使用的 ticker 不一定一致(比如 EchoStar,
    Wikipedia 用 ECHO, SEC 官方注册的却是 SATS), 多一层映射就多一个
    对不上的风险; 而 Wikipedia 给出的 CIK 本身就是可以直接用的,
    没必要绕这一圈。
    """

    # TODO: 实现
    # def _fetch_one(self, cik): ...
    # def _parse_facts(self, raw): ...

    def fetch(self) -> dict[str, str]:
        universe = load_cached_universe()

        url_map = {
            str(row.ticker): URL_TEMPLATE.format(cik=str(row.cik), concept=CONCEPT)
            for row in universe.itertuples(index=False)
        }

        logger.info(f"正在批量生成网址中, 共 {len(url_map)} 只 ...")
        logger.info(url_map)

        # TODO: 当前 fetch 只返回 URL 映射表, 还没有真正抓取 companyconcept facts,
        # 完成 _fetch_one / _parse_facts 之后, 这里最终应改回返回 pd.DataFrame,
        # 与 DataSource 基类的 fetch() -> pd.DataFrame 契约保持一致
        return url_map


if __name__ == "__main__":
    F = FetchEdgar()
    F.fetch()
