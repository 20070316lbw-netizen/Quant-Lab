"""基础价量因子: 目前只有 prices 表(价量数据)可用, EDGAR 基本面还没打通
(edgar.py 的 _fetch_one/_parse_facts 还是 TODO), 所以经典的 size/value
因子先放一放, 等 book equity 抓下来再补。

这里先做三类, 对应 Gu-Kelly-Xiu (2020) 里 price trend / volatility /
liquidity 这几个大类特征, 树模型直接吃这几列就能跑起来:
- momentum:   动量, 过去 N 期收益
- volatility: 波动率, 过去 N 期日收益率标准差
- liquidity:  流动性, 过去 N 期日均成交额
- 52 周高点距离: George & Hwang (2004) 的 52-week high 效应

跟 labels/future_return.py 反过来: 那边故意往未来看(因为是标签),
这里所有函数都只能往过去看(因为是特征) —— 如果哪天不小心在这个文件里
写出 shift(负数), 说明八成把方向搞反了。
"""
from __future__ import annotations

import pandas as pd


def daily_return(df: pd.DataFrame, price_col: str = "close") -> pd.Series:
    """逐 ticker 日收益率, 是动量/波动率因子的共同基础。"""
    return df.groupby(level="ticker")[price_col].pct_change()


def momentum(
    df: pd.DataFrame,
    window: int = 21,
    skip: int = 1,
    price_col: str = "close",
) -> pd.Series:
    """过去 window 期累计收益, 默认跳过最近 skip 期。

    跳过最近一段时间是经典动量因子的做法(Jegadeesh & Titman):
    最近几天的收益容易受短期反转效应干扰, 跳过之后信号更干净。
    跟 labels 里 make_label() 的 enter/exit_ 是同一个"shift 两次再相除"
    的写法, 只是时间方向反过来(那边往未来 shift, 这里往过去 shift)。
    """
    close = df.groupby(level="ticker")[price_col]
    p_recent = close.shift(skip)
    p_past = close.shift(skip + window)
    return p_recent / p_past - 1


def volatility(df: pd.DataFrame, window: int = 21, price_col: str = "close") -> pd.Series:
    """过去 window 期日收益率的标准差, 衡量近期波动大小。"""
    ret = daily_return(df, price_col)
    return ret.groupby(level="ticker").transform(lambda s: s.rolling(window).std())


def liquidity(
    df: pd.DataFrame,
    window: int = 21,
    price_col: str = "close",
    volume_col: str = "volume",
) -> pd.Series:
    """过去 window 期日均成交额(close * volume), 衡量流动性。

    TODO: 现在只有价量数据, 没有流通股本, 算不出真正的换手率
    (turnover = volume / shares_outstanding); EDGAR 的 shares outstanding
    接进来之后, 可以把这个换成更标准的换手率。
    """
    dollar_volume = df[price_col] * df[volume_col]
    return dollar_volume.groupby(level="ticker").transform(lambda s: s.rolling(window).mean())


def high_52w_proximity(df: pd.DataFrame, window: int = 252, price_col: str = "close") -> pd.Series:
    """当前价格相对过去 window 期最高价的距离(52 周高点效应, George & Hwang 2004)。

    min_periods 设得比 window 小: 数据不足一年时也能算出值, 只是早期
    "52 周高点"其实是"不到 52 周里的高点", 精度会打折扣。
    """
    rolling_max = df.groupby(level="ticker")[price_col].transform(
        lambda s: s.rolling(window, min_periods=window // 4).max()
    )
    return df[price_col] / rolling_max - 1


def make_features(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    """把上面几个因子拼成一张特征表, 直接喂给 models/tree_models.py。

    注意: df 由调用方(比如 pipeline/train.py)传入, 这里不负责加载数据
    ——原因见 labels/future_return.py 那次踩坑: 函数内部重新查库会导致
    X 和 y 各查一次、index 对不齐还不报错。

    Returns:
        pd.DataFrame: index 与 df 一致((date, ticker) MultiIndex), 列为
        各个特征。早期几百行会是 NaN(窗口不够长), 训练前需要 dropna,
        并且要跟 labels 对齐后一起 dropna(否则两边 NaN 的行对不上)。
    """
    return pd.concat(
        {
            "mom_1m": momentum(df, window=21, price_col=price_col),
            "mom_3m": momentum(df, window=63, price_col=price_col),
            "mom_6m": momentum(df, window=126, price_col=price_col),
            "mom_12m": momentum(df, window=252, price_col=price_col),
            "reversal_1w": momentum(df, window=5, skip=0, price_col=price_col),
            "vol_21d": volatility(df, window=21, price_col=price_col),
            "liquidity_21d": liquidity(df, window=21, price_col=price_col),
            "high52w_proximity": high_52w_proximity(df, price_col=price_col),
        },
        axis=1,
    )


if __name__ == "__main__":
    from quant_lab.data.loader import load_price_panel

    panel = load_price_panel(start="2024-01-01", end="2024-06-30")
    features = make_features(panel)
    print(features.shape)
    print(features.dropna().head(3))
