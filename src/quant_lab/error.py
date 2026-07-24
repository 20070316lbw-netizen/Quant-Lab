"""定义所有错误的基类"""

# from typing import TYPE_CHECKING

# if TYPE_CHECKING:
    # import pandas as pd

class QuantLabError(Exception):
    """项目所有自定义异常的根。捕获它 = 捕获本项目抛出的一切异常。"""


class YahooFetchError(QuantLabError):
    """Yahoo 数据抓取相关的错误"""

class WikiFetchError(QuantLabError):
    """Wiki 数据抓取相关错误。"""


class SchemaInitializationError(QuantLabError):
    """数据库 schema 初始化失败。"""


class UniverseLoadError(QuantLabError):
    """Universe 快照写入失败或输入不满足写入约束。"""


class EdgarFetchError(QuantLabError):
    """EDGAR 数据抓取相关的错误。"""

    def __init__(self, cik: str, status_code: int) -> None:
        self.cik = cik
        self.status_code = status_code

        super().__init__(f"CIK {cik} 抓取失败, 状态码 {status_code}")
        


class PointInTimeError(QuantLabError):
    """点位对齐相关的错误,比如用了 reporting period 而非 filed date。"""
