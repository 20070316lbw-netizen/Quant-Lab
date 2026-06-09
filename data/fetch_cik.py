# 用于获取 EDGAR 的cik映射表
# https://www.sec.gov/files/company_tickers.json

import requests
import sys
from io import StringIO
import time
from pathlib import Path
import pandas as pd 
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

URL = "https://www.sec.gov/files/company_tickers.json"

HEADERS = {"User-Agent": "liu 20070316lbw@gmail.com"}

def fetch_origin_json() -> dict:
    try:
        req = requests.get(URL, headers=HEADERS)   
        req.raise_for_status()
        raw = pd.read_json(StringIO(req.text)).T    # cik_str 现在是整数, 要先转换成字符串才行
        raw['cik'] = raw["cik_str"].astype(str).str.zfill(10)   # .str.zfill(10) 代表左边补零到 10 位
        # pandas 要求你先用 .str 访问器,才能调 zfill、upper、replace 这些字符串方法
        # 直接 .zfill(10) 会报错,因为那是单个字符串的方法,不是 Series 的
        
        print(raw)
        return raw

    except ConnectionError as c:
        logger.error(f"抓取失败 -{c}")
        return dict()


if __name__ == "__main__":
    fetch_origin_json()