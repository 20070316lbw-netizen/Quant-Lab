""""""

from __future__ import annotations

from io import StringIO
from pprint import pprint

import pandas as pd
import requests
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator

from quant_lab.error import WikiFetchError

_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class SP500Universe(BaseModel):
    """校验通过的一条 S&P 500 成分股记录, 校验通过才允许入库。"""

    ticker      : str
    company_name: str
    cik         : str = Field(
        pattern     = r"\d{10}$",
        description ="SEC CIK, 固定 10 位数字, 不足的时候补 0",
    )
    # ^\d{10}$：^ $ 锁定首尾避免部分匹配混过, \d{10} 要求恰好 10 位数字


    @field_validator("cik", mode="before")
    @classmethod
    def _pad_cik(cls, v: str) -> str:
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
        return v.strip()


def fetch_sp500_constituents() ->list[SP500Universe]:
    """从维基百科抓取当前 S&P 500 成分股列表, 逐条校验后返回。

    Returns:
        list[SP500universe]: 校验通过的成分股列表。

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
        raise WikiFetchError(f"")
    


