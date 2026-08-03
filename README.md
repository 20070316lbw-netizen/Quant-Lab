# Quant-Lab

[![CI](https://github.com/20070316lbw-netizen/Quant-Lab/actions/workflows/ci.yml/badge.svg)](https://github.com/20070316lbw-netizen/Quant-Lab/actions/workflows/ci.yml)

以论文复现驱动的量化研究项目。目前的数据层使用 PostgreSQL 保存价格和股票池数据，并通过 Pandas MultiIndex 向研究代码提供数据。

## Continuous Integration

每次推送代码或创建 Pull Request 时，GitHub Actions 会安装项目依赖并运行 PostgreSQL loader 的离线测试。

本地运行同一组测试：

```bash
uv run pytest tests/test_loader.py -q
```

## Research

- [Fama–French 三因子复现计划](research/README.md)
- [Jegadeesh–Titman 1993 动量复现](research/replications/jegadeesh_titman_1993/README.md)
