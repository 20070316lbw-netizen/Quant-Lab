"""玩具脚本: 体会抽象类的两层威力"""
from abc import ABC, abstractmethod

import pandas as pd


class DataSource(ABC):
    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        ...


# ---------- 两个守约的实现 ----------

class FakeYahoo(DataSource):
    def fetch(self) -> pd.DataFrame:
        return pd.DataFrame({"ticker": ["AAPL"], "close": [201.5]})


class FakeEdgar(DataSource):
    def fetch(self) -> pd.DataFrame:
        return pd.DataFrame({"cik": ["0000320193"], "equity": [62_000_000_000]})


# ---------- 一个忘了实现 fetch 的叛徒 ----------

class LazySource(DataSource):
    def hello(self):
        print("我什么都没实现")


# ---------- 威力二的关键: 下游代码 ----------

def run_pipeline(sources: list[DataSource]) -> None:
    """注意: 这个函数对 Yahoo/EDGAR 一无所知, 它只认识 DataSource"""
    for src in sources:
        df = src.fetch()
        print(f"{type(src).__name__} 交付了 {len(df)} 行数据")


if __name__ == "__main__":
    # 实验 1: 强制力
    try:
        DataSource()
    except TypeError as e:
        print(f"[实验1a] 抽象类本身拒绝实例化: {e}")

    try:
        LazySource()
    except TypeError as e:
        print(f"[实验1b] 不完整的实现也被拒绝: {e}")

    # 实验 2: 多态 —— 这才是主菜
    run_pipeline([FakeYahoo(), FakeEdgar()])