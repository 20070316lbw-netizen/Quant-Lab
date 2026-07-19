from __future__ import annotations

import pandas as pd
from loguru import logger

from quant_lab.sources.edgar import FetchEdgar


def get_dataframe_and_output_example() -> pd.DataFrame:

    """先拿到 FetchEdgar() 内部 fetch() 输出的 pd.Dataframe"""
    F = FetchEdgar()
    df = F.fetch()
    """
    liu@liudeMacBook-Air Quant-Lab % uv run python -m test.test_universe_dataframe
       cik_str ticker              title         cik
    0      1045810   NVDA        NVIDIA CORP  0001045810
    1      1652044  GOOGL      Alphabet Inc.  0001652044
    2       320193   AAPL         Apple Inc.  0000320193
    3       789019   MSFT     MICROSOFT CORP  0000789019
    4      1018724   AMZN     AMAZON COM INC  0001018724
    ...        ...    ...                ...         ...
    10360   312070    GRN  BARCLAYS BANK PLC  0000312070
    10361   312070    VXX  BARCLAYS BANK PLC  0000312070
    10362   312070    VXZ  BARCLAYS BANK PLC  0000312070
    10363   312070   TAPR  BARCLAYS BANK PLC  0000312070
    10364   312070  JJETF  BARCLAYS BANK PLC  0000312070

    [10365 rows x 4 columns]
    """

    for cik, name in zip(df["cik"], df["ticker"]):
        logger.info(f"目前在{cik} --- {name}")
    return df
    


if __name__ == "__main__":
    get_dataframe_and_output_example()