"""数据源抽象层: 定义所有数据源必须遵守的契约"""
from abc import ABC, abstractmethod

import pandas as pd


class DataSource(ABC):
    """所有数据源的基类。

    实现者契约:
    - fetch() 成功时返回非空 DataFrame
    - 失败时记录日志, 直接 raise

    # TODO:
    # 后续统一定义 DataFrame Schema 规范
    # 避免不同 DataSource 返回完全不同字段导致下游 Feature/Model 出现大量特殊处理
    """

    # TODO:
    # 后续考虑增加 name/schema/version 等元信息接口
    # 便于日志记录、数据校验和数据源管理

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        """抓取数据并返回 DataFrame。

        Returns:
            pd.DataFrame: 数据内容, 列结构由具体实现定义并在其 docstring 中声明。

        TODO:
            当前只约束返回 DataFrame。
            后续可增加字段校验、空值规则和索引规范(date/ticker 等)。
        """
        # TODO: 如果未来引入 Protocol 或更复杂插件系统，可重新评估 ABC 的必要性
        raise NotImplementedError