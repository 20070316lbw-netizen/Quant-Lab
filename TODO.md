# 项目 TODO 清单

> 本清单由散落在各文件中的 TODO 注释整理、核实、去重而来(20260701)。
> 原文件内联 TODO 注释建议后续逐步删除,以此文件为唯一入口。

---

## 🔴 阻塞性 bug(优先修)

- [ ] `pipeline/build_db.py`:`YahooPrices(row ticker, period=period)` 缺少点号,
      应为 `row.ticker`,当前会直接抛语法错误,`build()` 跑不起来。
- [ ] `tests/test_universe_dataframe.py`:`from quant_lab.data.edgar import FetchEdgar`
      导入路径错误,`FetchEdgar` 实际定义在 `quant_lab.sources.edgar`,测试无法运行。
- [ ] `database/schema.sql` 与 `storage/duckdb_store.py` 里的 `PRICE` 建表语句重复定义,
      且已出现分歧:`volume` 字段前者是 `DOUBLE`,后者是 `BIGINT`。实际生效的是
      `duckdb_store.py`(代码里真正执行的那份),需要决定 `schema.sql` 是否废弃或改为
      唯一数据源、由代码读取它而不是各自维护一份。

---

## 🟡 数据层 · 价量(`sources/yahoo.py`)

- [ ] 网络请求缺少显式 timeout/重试控制,偶发卡死或失败无法恢复
- [ ] 只捕获了"空数据"情况,yfinance 的网络异常/限流异常未捕获,应统一转成 `YahooFetchError`
- [ ] `date` 列当前被转成 Python `date` object,而 DuckDB/main.py 读出来是
      `datetime64[us]`,入库前需要确认全链路统一用哪种类型(**原 20260620 TODO 对应项,
      核实后确认尚未完成**)
- [ ] 假设 yfinance 一定返回完整 OHLCV 字段,应在选列前做 schema 校验并给出清晰报错
- [ ] `TEMP_DIR`(定义在 `config.py`)名字像目录但实际是文件路径(`aapl.csv`),
      建议改名为 `TEMP_FILE` / `TEMP_CSV_PATH`,`yahoo.py` 里 `__main__` 调试代码同步修正
- [x] ~~f-string 引号冲突~~:已核实,`f"...{df['date'].min()}..."` 外双内单引号类型不同,
      不会报错,原 TODO 注释可以删除

## 🟡 数据层 · 标的池(`sources/fetch_universe.py`)

- [ ] 增加 `requests.RequestException` 捕获,统一转换成项目内部异常类型
- [ ] Wikipedia 页面结构变更后 `pd.read_html(...)[0]` 可能不再是成分股表,需要增加表结构校验
- [ ] 假设 `Symbol`/`Security`/`CIK` 三列必然存在,应先校验列名再重命名
- [ ] Wikipedia 数据出现缺失值时,`cik` 列 `astype(str)` 可能产出字符串 `'<NA>'`,需单独处理
- [ ] 建议记录抓取数量/样本范围日志,便于排查 universe 变化
- [ ] `__main__` 里的 `print(df)` 改成 `logger` 或迁移进单元测试

## 🔴 数据层 · 基本面(`sources/edgar.py`)—— 当前项目主焦点

- [ ] `_fetch_one(cik)`:抓取单个公司的 `companyconcept` facts,尚未实现
- [ ] `_parse_facts(raw)`:解析 XBRL facts、按 filing date 做 point-in-time 对齐,尚未实现
- [ ] `fetch()` 当前只返回 CIK 映射表,还没有真正抓 book equity / shares outstanding
- [ ] `_load_cik_map` 返回 DataFrame,查询体验不如 dict(`cik_map["AAPL"]` 一步到位)。
      设计上可以 `set_index("ticker")["cik"].to_dict()` 转换,内部用 dict、对外看需要再定
- [X] 请求缺少 timeout,网络卡住时会无限等待
- [ ] **实际 bug**:`except ConnectionError` 捕获的是 Python 内置异常,但 `requests` 抛出的是
      `requests.exceptions.RequestException` 及其子类,当前写法基本捕获不到 `requests` 的
      网络异常,应改成 `except requests.RequestException`
- [X] `fetch()` 里的 `print(cik_map)` 调试输出,接入 pipeline 前应改 `logger.debug` 或删除

## 🟢 数据源抽象层(`sources/base.py`)

- [ ] 统一定义 DataFrame Schema 规范(列结构、空值规则、索引规范如 date/ticker),
      避免各 DataSource 返回结构不一致导致下游大量特殊处理
- [ ] 考虑给 `DataSource` 增加 `name` / `schema` / `version` 等元信息接口,便于日志和管理
- [ ] (低优先级/设计笔记)若未来引入 `Protocol` 或更复杂插件系统,重新评估 `ABC` 的必要性

## 🟢 配置(`config.py`)

- [ ] `DATABASE_PATH` 写死在项目目录,后续可支持环境变量覆盖,方便部署/测试
- [ ] `get_duckdb()` 后续可统一注入 DuckDB 配置(PRAGMA、线程数、只读模式等)
- [ ] `get_duckdb()` 在 `DATABASE_PATH` 父目录不存在时会报错;目前 `build_db.py` 里手动
      `mkdir` 绕过了这个问题,但直接调用 `get_duckdb()` 仍会炸,建议挪进函数内部自动创建

## 🟡 Pipeline(`pipeline/build_db.py`)

- [ ] 文档字符串参数名写成 `tickers_limit`,实际参数是 `ticker_limit`,需统一
- [ ] 文档说默认取 100 只,实际默认值是 503,文档与实现不一致,需修正其一
- [ ] 每次 `build()` 都重新抓 Wikipedia,应优先读取 `SP500_CACHE_PATH` 缓存,并提供强制刷新选项
- [ ] `ticker_limit` 未做边界校验(0/负数/超过 universe 长度时行为不明确)
- [ ] 当前串行抓取全部股票会比较慢,后续可考虑限速并发或断点续跑
- [x] ~~upsert 的主键/冲突策略未确认~~:已在 `duckdb_store.py` docstring 里说明,
      是 `INSERT OR REPLACE + 主键 (date, ticker)`,幂等写入,不会产生重复行
- [ ] EDGAR 数据接入(依赖上面 edgar.py 的核心实现完成)
- [ ] 当前 `except Exception` 捕获过宽,会掩盖代码本身的 bug,应优先捕获
      `QuantLabError` / 网络异常等预期错误类型
- [ ] 即使部分 ticker 抓取失败,最后仍统一打印 `"build SUCCESSFUL"`,应统计成功/失败数量
      并在日志里体现,而不是笼统报成功

## 🗑️ 待清理

- [ ] `tests/data/testlogger.py`:独立重复实现了一份 SP500
      抓取逻辑,与 `sources/universe/fetch.py::fetch_sp500_universe` 功能重复,像早期探索代码,
      建议删除或明确说明保留原因
- [ ] `storage/paths.py`、`features/basic.py`、`labels/future_return.py`、
      `models/base.py`、`pipeline/predict.py`、`pipeline/train.py`:目前均为空文件占位,
      待因子计算层/验证层开工后再填充,暂不算 bug,列出以便追踪进度

---

## 项目进度(与 README 对齐)

- [x] 数据层:价量(`fetch_universe` / `YahooPrices` / database),核心功能可用,细节 TODO 见上
- [ ] 数据层:基本面(SEC EDGAR, point-in-time)← **当前焦点,见上方 🔴 部分**
- [ ] 因子计算层(`features/`, `labels/` 目前为空)
- [ ] 验证层
