from quant_lab.connection import get_duckdb
with get_duckdb() as con:
    df = con.execute("SELECT date FROM prices LIMIT 5").df()

print(df.dtypes)

"""
date    datetime64[us]
dtype: object
"""