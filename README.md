# learn_quant

复现学术因子论文,用作量化实习的项目凭证.
方法论:**论文复现驱动** —— 不先建基础设施,而是锁定一篇论文,倒推出复现它所需的最小模块,只造该造的。

---

## 当前复现目标

**Fama & French (1993), "Common risk factors in the returns on stocks and bonds"**

复现 FF3 三因子模型,并用论文的验证方式检验因子有效性。

数据约束(诚实声明):
- Universe:S&P 500(论文原文为全 NYSE/AMEX/NASDAQ)
- 样本期:约 2009 至今(受 SEC XBRL 强制披露起始时间限制,非原文 1963–1991)
- 价量数据:yfinance(日频 OHLCV)
- 基本面数据:SEC EDGAR(point-in-time,带 filing date)

---

## 论文完成了什么 → 我们要照着完成什么

论文的最终交付物拆成三件事,对应三个大组件层。

### 1. 数据层 —— 把论文需要的原始输入凑齐

论文需要三类输入:每只股票的**收益**、**市值**、**账面市值比 (B/M)**。
- 价量数据(收益、market cap 的价格部分)—— yfinance,**已基本完成**
- 基本面数据(账面价值 book equity、流通股数 shares outstanding)—— SEC EDGAR,**待建**
- **关键要求:point-in-time**。基本面数据必须按「财报实际提交日 (filing date)」对齐,不能用 period-end date,否则引入 look-ahead bias。这是本项目最核心的数据工程环节。

### 2. 因子计算层 —— 按论文方式造出三个因子

论文用 2×3 排序构造因子:每年按市值分 2 组(大/小),按 B/M 分 3 组(30/70 断点),交叉成 6 个市值加权组合。
- **Rm − Rf**:市场组合收益(S&P 500 市值加权 proxy)减无风险利率
- **SMB(规模)**:三个小市值组合的等权平均 − 三个大市值组合的等权平均
- **HML(价值)**:大小价值股的等权平均 − 大小成长股的等权平均
- 配套:日频→月频收益聚合、B/M 计算、2×3 分组器

### 3. 验证层 —— 用论文的检验方式证明因子有效

论文用 25 个(5×5,按 size 和 B/M 排序)测试组合做时序回归,检验三因子能否解释截面收益、截距 (alpha) 是否显著为零。
- 25 测试组合构造
- 三因子时序回归 + 截距检验
- 稳健性验证(后续接入):WFO / TimeSeriesSplit / Monte Carlo

---

## 进度

- [x] 数据层:价量(fetch_universe / fetch_stock / database)
- [ ] 数据层:基本面(SEC EDGAR,point-in-time)← **当前焦点**
- [ ] 因子计算层
- [ ] 验证层

---

