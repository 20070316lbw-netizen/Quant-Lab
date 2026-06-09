# 用来抓取 EDGAR 股票

# url = "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/StockholdersEquity.json"
# 这里硬编码了 AAPL 的股票代码 0000320193,原因是他只吃 10 位数字, 需要手动补齐

import requests
import sys
from io import StringIO
import time
from pathlib import Path
import pandas as pd 
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/StockholdersEquity.json"

HEADERS = {"User-Agent": "liu 20070316lbw@gmail.com"}

def fetch_edgar_stock() -> pd.DataFrame:
    try:
        resp = requests.get(URL, headers = HEADERS)
        resp.raise_for_status()

        raw = resp.json()   # 现在是 Dict

        records = raw["units"]["USD"]   # 现在是 list of dict
        df = pd.DataFrame(records)

        print(df)

        return df

    except ConnectionError as c:
        logger.error(f"抓取失败 -{c}")
        return pd.DataFrame()
    

if __name__ == "__main__":
    fetch_edgar_stock()
