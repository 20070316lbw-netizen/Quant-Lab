import requests
from io import StringIO
import pandas as pd
from loguru import logger

from pipeline.base import DataSource


# ---------------- 定义全局常量 ---------------------
HEADERS = {"User-Agent": "liu 20070316lbw@gmail.com"}       # EDGAR 抓取要求
CIK_URL = "https://www.sec.gov/files/company_tickers.json"      # 抓取 cik 映射表
AAPL_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/StockholdersEquity.json"      # 抓取尝试

class FetchEdgar(DataSource):
    """整个抓取 EDGAR 的大类, 继承 base.py 下的 Datasource 类 """

    # TODO: 实现
    # def _load_cik_map(self): ...
    # def _fetch_one(self, cik): ...
    # def _parse_facts(self, raw): ...

    def fetch(self) -> pd.DataFrame:
        cik_map = self._load_cik_map()

        print(cik_map)

        return cik_map


        ...

    def _load_cik_map(self) -> pd.DataFrame:

        # TODO 
        # 最终返回的是 Dataframe 而不是 dict
        # "映射表"这个东西的天然形态就是 dict，查询就是 cik_map["AAPL"] 一步到位
        # DataFrame 在转置后，ticker 和 cik 是两列，pandas 有现成路径
        # 比如用 ticker 那列 set_index，然后取 cik 列（此时是 Series），Series 上有个 to_dict() 方法

        try:
            req = requests.get(CIK_URL, headers = HEADERS)
            req.raise_for_status()

            cik_map = pd.read_json(StringIO(req.text)).T

            cik_map["cik"] = cik_map["cik_str"].astype(str).str.zfill(10)
            # .str.zfill(10) 代表左边补零到 10 位
            # pandas 要求你先用 .str 访问器,才能调 zfill、upper、replace 这些字符串方法
            # 直接 .zfill(10) 会报错,因为那是单个字符串的方法,不是 Series 的

            return cik_map

        except ConnectionError as e:
            logger.error(f"抓取失败 -{e}")
            raise


if __name__ == "__main__":
    F = FetchEdgar()
    F.fetch()
