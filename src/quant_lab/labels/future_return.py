"""定义标签"""
from __future__ import annotations

import pandas as pd

def make_label(
        df          : pd.DataFrame,
        n_periods   : int = 5,
        price_col   : str = "close",
        gap         : int = 1,
) -> pd.Series:
    """
    Args:
        df: MultiIndex (datetime, instrument) DataFrame, 至少含 price_col
        n_periods: 持仓天数 (预测未来多少天的累计收益)        
        price_col: 用哪列价 (默认 close)
        gap: 当前 t 和进场之间隔几期 (默认 1, 即 t+1 开仓, t+1+N 平仓)

    Returns:
        pd.Series: 一列数据用于输入模型进行训练, 为未来 N 日 (默认5天) 的收益率
    """

    # 先用 `groupby()` 将所有股票的 `close`列按照 level = `ticker` 给索引分组
    # 我们这里已经是 MultIndex 了, 所以要按索引分组, 话说...不写 `level=` 好像会报错来着 
    close_series = df[price_col].groupby(level="ticker")

    # 接着定义入场 (enter) 和跑路 (exit_) ...千万不要用 `exit`, 记得加一个下划线
    # 还有就是, 我看的是未来 N 天收益 ,可千万别往后看收益了
    enter = close_series.shift(-gap)
    exit_ = close_series.shift(-gap - n_periods)

    label = (exit_ / enter - 1)
    return label



    

