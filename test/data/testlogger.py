import requests
import sys
from io import StringIO
import time
from pathlib import Path
import pandas as pd 
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import PROJECT_ROOT, SP500_CACHE_PATH

URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

class GetSP500List():
    @staticmethod
    def fetch_wiki() -> list[pd.DataFrame] | list:
        headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/120.0.0.0 Safari/537.36"
                    }
        logger.info("正在抓取 sp500 列表中...")
        try:
            response = requests.get(URL, headers=headers)
            response.raise_for_status()
            tables = pd.read_html(StringIO(response.text))
            logger.info(f"抓取成功")
        except Exception as e:
            logger.error(f"无法抓取 sp500 列表, -{e}")
            return list()
        
        list_page = tables[0]
        sp500 = list_page['Symbol'].str.replace(".", "-", regex=False).tolist()
        return sp500
    


if __name__ == "__main__":
    g = GetSP500List()
    result = g.fetch_wiki()
    