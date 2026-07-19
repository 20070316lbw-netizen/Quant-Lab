import pytest
import pandas as pd
from pydantic import ValidationError
from quant_lab.data.loader import RangeQuery, loader, build_sql
from quant_lab.data.schema_registry import TABLES


def test_range_query_valid():
    # 测试合法的 RangeQuery 请求
    req = RangeQuery(
        table="prices",
        columns=["open", "close"],
        start="2024-01-02",
        end="2024-01-05"
    )
    assert req.table == "prices"
    assert req.columns == ["open", "close"]
    assert req.start == "2024-01-02"
    assert req.end == "2024-01-05"

    # 确保 select_columns 包含索引和请求列，且无重复值
    expected_cols = list(dict.fromkeys(TABLES["prices"].index + ["open", "close"]))
    assert req.select_columns == expected_cols


def test_build_sql():
    # 测试 SQL 语句的动态生成
    req = RangeQuery(
        table="prices",
        columns=["open", "close"],
        start="2024-01-02",
        end="2024-01-05"
    )
    sql = build_sql(req)
    assert "SELECT date, ticker, open, close" in sql
    assert "FROM prices" in sql
    assert "WHERE date BETWEEN ? AND ?" in sql
    assert "ORDER BY date, ticker" in sql


def test_loader_execution():
    # 测试 loader 能否正常在 DuckDB 中执行并返回期望的 MultiIndex DataFrame
    req = RangeQuery(
        table="prices",
        columns=["open", "close"],
        start="2024-01-02",
        end="2024-01-05"
    )
    df = loader(req)

    # 验证返回的是 DataFrame 且不是空的
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        # 验证索引是 MultiIndex，且名称为 ['date', 'ticker']
        assert isinstance(df.index, pd.MultiIndex)
        assert df.index.names == ["date", "ticker"]
        # 验证返回的列除了被做成索引的列外，只有请求的 columns (open, close)
        assert list(df.columns) == ["open", "close"]


def test_invalid_table_validation():
    # 验证无效的表名会导致 Pydantic ValidationError，而不是 KeyError 异常崩溃
    with pytest.raises(ValidationError) as exc_info:
        RangeQuery(
            table="invalid_table_name",  # type: ignore
            columns=["open"],
            start="2024-01-01",
            end="2024-01-05"
        )
    # 错误应当归属于 table 字段校验
    assert "table" in str(exc_info.value)


def test_invalid_columns_validation():
    # 验证无效的列名会被 field_validator 拦截并报 ValueError
    with pytest.raises(ValidationError) as exc_info:
        RangeQuery(
            table="prices",
            columns=["open", "invalid_column_field"],
            start="2024-01-01",
            end="2024-01-05"
        )
    assert "prices 不支持字段: ['invalid_column_field']" in str(exc_info.value)


def test_missing_table_validation():
    # 验证缺失 table 时，不会因为 validate_columns 中 TABLES[table] 访问而报 KeyError
    with pytest.raises(ValidationError) as exc_info:
        RangeQuery(
            columns=["open"],  # type: ignore (缺少 table)
            start="2024-01-01",
            end="2024-01-05"
        )
    assert "Field required" in str(exc_info.value)
