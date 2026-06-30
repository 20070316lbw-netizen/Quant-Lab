"""
示例：如何使用 RangeQuery 和 loader 进行类型安全的数据加载
"""

from pydantic import ValidationError
from quant_lab.data.loader import RangeQuery, loader


def run_demo():
    print("=== 1. 执行合法查询 ===")
    # 构造一个合法的查询请求，获取价格表中的 open, close 字段
    req = RangeQuery(
        table="prices",
        columns=["open", "close"],
        start="2024-01-02",
        end="2024-01-05"
    )
    print(f"生成的 SQL 语句:\n{req}")

    # 获取 DataFrame
    df = loader(req)
    print("\n获取到的 DataFrame 前 5 行:")
    print(df.head())
    print(f"索引类型: {df.index.__class__.__name__}")
    print(f"索引名称: {df.index.names}")

    print("\n=== 2. 测试非法表名拦截 ===")
    try:
        RangeQuery(
            table="non_existent_table",  # type: ignore (为了测试运行时的 Pydantic 拦截)
            columns=["open"],
            start="2024-01-01",
            end="2024-01-05"
        )
    except ValidationError as e:
        print("成功拦截非法表名！Pydantic 报错信息：")
        print(e)

    print("\n=== 3. 测试该表不支持的非法列名拦截 ===")
    try:
        RangeQuery(
            table="prices",
            columns=["open", "invalid_col"],  # 'invalid_col' 不在 prices 的 schema.columns 中
            start="2024-01-01",
            end="2024-01-05"
        )
    except ValidationError as e:
        print("成功拦截非法列名！Pydantic 报错信息：")
        print(e)


if __name__ == "__main__":
    run_demo()
