"""数据源抽象层: 定义所有数据源必须遵守的契约"""
from abc import ABC, abstractmethod

import pandas as pd


class DataSource(ABC):
    """所有数据源的基类。

    实现者契约:
    - fetch() 成功时返回非空 DataFrame
    - 失败时记录日志, 直接 raise 
    """

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        """抓取数据并返回 DataFrame。

        Returns:
            pd.DataFrame: 数据内容, 列结构由具体实现定义并在其 docstring 中声明。
        """
        raise NotImplementedError