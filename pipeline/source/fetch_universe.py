import requests
import sys
from io import StringIO
import time
from pathlib import Path
import pandas as pd 
from loguru import logger

from config import PROJECT_ROOT, SP500_CACHE_PATH
from database import get_last_date

URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def main():
    headers = {
        "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
        }
    
    logger.info("正在抓取股票列表 ing ...")
    response = requests.get(URL, headers = headers)
    response.raise_for_status()
    raw_page = pd.read_html(StringIO(response.text))

    sp500 = raw_page[0]
    # print(sp500)
    #         Symbol             Security             GICS Sector  ...  Date added      CIK      Founded
    # 0      MMM                   3M             Industrials  ...  1957-03-04    66740         1902
    # 1      AOS          A. O. Smith             Industrials  ...  2017-07-26    91142         1916
    # 2      ABT  Abbott Laboratories             Health Care  ...  1957-03-04     1800         1888
    # 3     ABBV               AbbVie             Health Care  ...  2012-12-31  1551152  2013 (1888)
    # 4      ACN            Accenture  Information Technology  ...  2011-07-06  1467373         1989
    # ..     ...                  ...                     ...  ...         ...      ...          ...
    # 498    XYL           Xylem Inc.             Industrials  ...  2011-11-01  1524472         2011
    # 499    YUM          Yum! Brands  Consumer Discretionary  ...  1997-10-06  1041061         1997
    # 500   ZBRA   Zebra Technologies  Information Technology  ...  2019-12-23   877212         1969
    # 501    ZBH        Zimmer Biomet             Health Care  ...  2001-08-07  1136869         1927
    # 502    ZTS               Zoetis             Health Care  ...  2013-06-21  1555280         1952
    # 这里我准备抓取 ["Symbol"] 和 ["Security"]

    sp500 = sp500.rename(columns = {
        "Symbol" : "symbol",
        "Security" : "security"
    })
    # print(sp500)
    #         symbol             security             GICS Sector  ...  Date added      CIK      Founded
    # 0      MMM                   3M             Industrials  ...  1957-03-04    66740         1902
    # 1      AOS          A. O. Smith             Industrials  ...  2017-07-26    91142         1916
    # 2      ABT  Abbott Laboratories             Health Care  ...  1957-03-04     1800         1888
    # 3     ABBV               AbbVie             Health Care  ...  2012-12-31  1551152  2013 (1888)
    # 4      ACN            Accenture  Information Technology  ...  2011-07-06  1467373         1989
    # ..     ...                  ...                     ...  ...         ...      ...          ...
    # 498    XYL           Xylem Inc.             Industrials  ...  2011-11-01  1524472         2011
    # 499    YUM          Yum! Brands  Consumer Discretionary  ...  1997-10-06  1041061         1997
    # 500   ZBRA   Zebra Technologies  Information Technology  ...  2019-12-23   877212         1969
    # 501    ZBH        Zimmer Biomet             Health Care  ...  2001-08-07  1136869         1927
    # 502    ZTS               Zoetis             Health Care  ...  2013-06-21  1555280         1952

    # [503 rows x 8 columns]
    # 这里成功转换,现在我们似乎只需要["symbol"] 和 ["security"] 这两列,准备直接建表,似乎这样不需要的就会消失

    if SP500_CACHE_PATH.exists():
        logger.info("文件存在,准备开始写入")
    else:
        logger.info("未发现文件,开始建 csv 文件")
        SP500_CACHE_PATH.parent.mkdir(parents = True, 
                                      exist_ok = True)
    
    sp500.to_csv(SP500_CACHE_PATH,
                 index = False,
                 encoding = "utf-8")
    logger.success("写入成功")

    return sp500

if __name__ == "__main__":
    main()
    
