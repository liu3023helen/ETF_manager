# portfolio_snapshots 表详解

## 一、主要用途

`portfolio_snapshots` 是一张**每日资产快照表**，记录整个投资组合在每个交易日的资产状况汇总。它的核心价值是：

> **把每一天的"全景照片"存下来，让你能回头看任何一天的资产情况。**

具体来说，它支撑了前端 **收益分析页（ProfitView）** 的全部图表和指标：

| 前端功能 | 依赖的快照字段 | 说明 |
|----------|---------------|------|
| 收益率走势曲线 | `snapshot_date`, `pnl_rate` | 每日收益率的折线图 |
| 总资产 vs 总投入曲线 | `total_assets`, `total_invested` | 两条线的对比走势 |
| 每日盈亏变动柱状图 | `total_pnl`（前后两天的差值） | 红绿柱状图 |
| 收益汇总指标卡 | `total_assets`, `total_pnl`, `pnl_rate`, `realized_pnl`, `fund_count` | 页面顶部四个数字 |
| 时间段收益对比 | 最新快照 vs N天前快照 | "近1周 +2.3%" 这类标签 |

### 为什么需要这张表？不能实时算吗？

不能，原因有两个：

1. **历史净值会变**：`daily_quotes` 表只存了每天的净值，但如果那天你还没买入某只基金，即使有净值数据，那天的持仓份额也是 0。持仓份额需要通过回放交易记录逐日累积得出。
2. **性能**：如果每次打开收益页面都要从第一笔交易开始回放几百天的数据，太慢了。快照表相当于**预计算的缓存**，查询直接 SELECT 即可。

---

## 二、字段定义

```sql
CREATE TABLE portfolio_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,  -- 快照ID
    snapshot_date   TEXT NOT NULL UNIQUE,                -- 快照日期 (YYYY-MM-DD)
    total_assets    REAL DEFAULT 0,                      -- 当日总市值(元)
    total_invested  REAL DEFAULT 0,                      -- 截至当日的累计买入总金额(元)
    total_pnl       REAL DEFAULT 0,                      -- 当日浮动盈亏(元)
    pnl_rate        REAL DEFAULT 0,                      -- 当日收益率(%)
    realized_pnl    REAL DEFAULT 0,                      -- 截至当日的累计已实现收益(元)
    fund_count      INTEGER DEFAULT 0,                   -- 当日持仓基金数(份额>0的)
    created_at      TEXT                                 -- 记录创建/更新时间
);
```

### 字段详细说明

| 字段 | 含义 | 举例 |
|------|------|------|
| `snapshot_date` | 这张快照对应哪一天 | `2026-03-14` |
| `total_assets` | 那一天所有持仓基金的市值之和 | `2381.05`（元） |
| `total_invested` | 从第一笔交易到那天为止，累计花了多少钱买基金 | `9400.00`（元） |
| `total_pnl` | 浮动盈亏 = 总市值 - 总持有成本（**不是** 总市值 - 总投入） | `274.15`（元） |
| `pnl_rate` | 收益率 = 浮动盈亏 / 总持有成本 × 100 | `13.01`（%） |
| `realized_pnl` | 累计已实现收益 = 历次卖出的（卖出回收金额 - 卖出份额对应的成本） | `156.80`（元） |
| `fund_count` | 那天有多少只基金是有持仓的（份额 > 0） | `2` |

> **注意区分**：
> - `total_pnl`（浮动盈亏）的分母是**持有成本**（份额 × 加权平均成本价），不是 `total_invested`（累计买入总金额）
> - `total_invested` 包含了已经卖掉的基金的买入金额（只增不减）

---

## 三、数据来源与依赖关系

快照表的数据**不是**直接从某个 API 拉取的，而是通过**回放两张表的数据**计算生成的：

```
┌─────────────────┐     ┌─────────────────┐
│  trade_records   │     │  daily_quotes    │
│  (交易记录表)     │     │  (每日净值表)     │
│                  │     │                  │
│ fund_code        │     │ fund_code        │
│ record_type      │     │ quote_date       │
│ record_date      │     │ close_price      │
│ amount           │     │                  │
│ shares           │     │                  │
│ nav              │     │                  │
│ exec_status      │     │                  │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         │    generate_snapshots.py
         │    (回放计算脚本)
         │                        │
         ▼                        ▼
┌──────────────────────────────────────────┐
│         portfolio_snapshots              │
│         (每日资产快照表)                   │
│                                          │
│  snapshot_date, total_assets,            │
│  total_invested, total_pnl,              │
│  pnl_rate, realized_pnl, fund_count     │
└────────────────────┬─────────────────────┘
                     │
                     │  API: /api/snapshots
                     │  API: /api/snapshots/summary
                     ▼
┌──────────────────────────────────────────┐
│         前端 ProfitView.vue              │
│                                          │
│  • 收益率走势图                           │
│  • 总资产 vs 总投入曲线                    │
│  • 每日盈亏变动柱状图                      │
│  • 收益汇总指标卡                         │
│  • 时间段收益对比标签                      │
└──────────────────────────────────────────┘
```

### 上游数据源

| 数据源 | 表名 | 使用的字段 | 用途 |
|--------|------|-----------|------|
| 交易记录 | `trade_records` | `fund_code`, `record_type`, `record_date`, `amount`, `shares`, `nav` | 通过逐笔回放计算每天每只基金的**持仓份额**和**成本价** |
| 每日净值 | `daily_quotes` | `fund_code`, `quote_date`, `close_price` | 提供每天的基金净值，用于计算**当日市值** |

### 过滤条件

- `trade_records` 只使用 `exec_status = '已执行'` 的记录
- `trade_records` 只处理 `record_type` 为 `买入`、`卖出`、`定投` 的记录（忽略 `信号` 类型）
- `daily_quotes` 的 `quote_date` 决定了哪些天会生成快照（只有有净值数据的交易日才会有快照）

---

## 四、计算逻辑详解

### 整体流程

```
1. 拉取全部已执行的交易记录（按日期升序）
2. 拉取全部基金的每日净值数据
3. 确定所有交易日（有净值数据的日期）
4. 从第一笔交易日开始，逐日推进：
   ├── 4a. 应用当天发生的交易 → 更新持仓状态
   ├── 4b. 用当日净值 × 持仓份额 → 计算当日市值
   ├── 4c. 汇总所有基金 → 得到组合级别的指标
   └── 4d. 写入一条快照记录
```

### 4a. 交易回放：每笔交易如何影响持仓状态

脚本在内存中维护一个持仓字典，结构为：

```python
holdings = {
    "009505": {
        "shares": 499.4,       # 当前持有份额
        "total_bought": 8200,  # 累计买入总金额
        "avg_price": 2.4088,   # 加权平均成本价
        "realized_pnl": 156.8, # 累计已实现收益
    },
    "009478": { ... },
}
```

#### 买入/定投

```
旧持有成本 = 旧份额 × 旧成本价
新份额 = 旧份额 + 买入份额
新成本价 = (旧持有成本 + 买入份额 × 买入净值) / 新份额    ← 加权平均
累计买入 += 买入金额
```

**举例**：持有 009505 的 200 份，成本价 2.00 元，再买入 100 份，净值 2.40 元：
- 旧持有成本 = 200 × 2.00 = 400 元
- 新份额 = 200 + 100 = 300 份
- 新成本价 = (400 + 100 × 2.40) / 300 = 640 / 300 = 2.1333 元

#### 卖出

```
卖出比例 = 卖出份额 / 当前持有份额          （不超过 1.0）
卖出成本 = 当前持有份额 × 成本价 × 卖出比例
已实现收益 += 卖出回收金额 - 卖出成本         ← 这一笔卖出赚了还是亏了
剩余份额 = 当前份额 - 卖出份额
```

**举例**：持有 300 份，成本价 2.1333 元，卖出 100 份，卖出价 2.50 元：
- 卖出比例 = 100 / 300 = 0.3333
- 卖出成本 = 300 × 2.1333 × 0.3333 = 213.33 元
- 卖出回收 = 100 × 2.50 = 250 元
- 这笔已实现收益 = 250 - 213.33 = **+36.67 元**

### 4b. 当日市值计算

对每只持仓基金（份额 > 0）：

```
当日市值 = 持有份额 × 当日净值
```

**净值取值优先级**（如果当天没有净值数据）：
1. 优先用 `daily_quotes` 中 `quote_date = 当天` 的 `close_price`
2. 没有则向前找最近一个有净值的日期（**最近历史净值兜底**）
3. 都没有则用 `avg_price`（成本价兜底）

### 4c. 组合级别汇总

```
total_assets   = SUM(每只基金的当日市值)
total_cost     = SUM(每只基金的 持有份额 × 成本价)
total_invested = SUM(每只基金的 累计买入总金额)      ← 含已清仓基金
total_pnl      = total_assets - total_cost           ← 浮动盈亏
pnl_rate       = total_pnl / total_cost × 100        ← 收益率
realized_pnl   = SUM(每只基金的 累计已实现收益)
fund_count     = COUNT(份额 > 0 的基金)
```

> **关键区分**：
> - `total_cost`（持有成本）= 当前持有的份额 × 加权平均成本价，**只反映当前还持有的部分**
> - `total_invested`（累计买入）= 历史上所有买入/定投的金额之和，**含已卖出的部分**
> - 收益率的分母是 `total_cost` 而非 `total_invested`

### 4d. 写入策略（UPSERT）

```sql
INSERT INTO portfolio_snapshots (snapshot_date, ...)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(snapshot_date) DO UPDATE SET
    total_assets = excluded.total_assets,
    ...
```

同一天重复运行不会产生重复记录，而是覆盖更新。

---

## 五、触发时机

快照表的数据**不是实时写入的**，需要手动或定时运行脚本生成：

| 场景 | 命令 | 说明 |
|------|------|------|
| 补录全部历史 | `python scripts/generate_snapshots.py` | 从第一笔交易开始，逐日计算所有快照。通常在首次部署或数据修复时运行 |
| 仅更新今日 | `python scripts/generate_snapshots.py today` | 只计算今天的快照。通常在每日拉取最新净值后运行 |

### 推荐的每日运行流程

```
1. 拉取最新净值数据 → 写入 daily_quotes 表
2. 运行 generate_snapshots.py today → 生成/更新今日快照
3. 前端打开收益页面 → 自动从 API 读取最新快照数据
```

### 什么时候需要全量重建快照？

- 修改了历史交易记录（增删改了买入/卖出记录）
- 补录了历史净值数据
- 发现快照数据不准需要修复

---

## 六、API 接口

快照数据通过后端 API 提供给前端：

### GET /api/snapshots

获取快照列表（用于绘制曲线图）。

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `date_from` | string | 起始日期（可选），格式 `YYYY-MM-DD` |
| `date_to` | string | 截止日期（可选），格式 `YYYY-MM-DD` |

**返回示例**：
```json
[
  {
    "date": "2025-12-01",
    "total_assets": 5231.05,
    "total_invested": 5000.00,
    "total_pnl": 231.05,
    "pnl_rate": 4.62,
    "realized_pnl": 0,
    "fund_count": 3
  },
  {
    "date": "2025-12-02",
    "total_assets": 5280.10,
    "total_invested": 5000.00,
    "total_pnl": 280.10,
    "pnl_rate": 5.60,
    "realized_pnl": 0,
    "fund_count": 3
  }
]
```

### GET /api/snapshots/summary

获取收益汇总指标（最新快照 + 各时间段对比）。

**返回示例**：
```json
{
  "latest": {
    "date": "2026-03-13",
    "total_assets": 2381.05,
    "total_invested": 9400.00,
    "total_pnl": 274.15,
    "pnl_rate": 13.01,
    "realized_pnl": 156.80,
    "fund_count": 2
  },
  "periods": [
    { "label": "近1周", "pnl_change": 52.30, "pnl_rate_change": 2.25, "start_date": "2026-03-06" },
    { "label": "近1月", "pnl_change": 120.50, "pnl_rate_change": 5.33, "start_date": "2026-02-13" },
    { "label": "近3月", "pnl_change": -80.20, "pnl_rate_change": -3.26, "start_date": "2025-12-14" }
  ]
}
```

**periods 的计算逻辑**：
```
pnl_change = 最新快照的 total_assets - N天前快照的 total_assets
pnl_rate_change = pnl_change / N天前快照的 total_assets × 100%
```

---

## 七、与其他表的完整关系图

```
                    ┌──────────────┐
                    │  fund_info   │ ← 基金基础信息（名称、分类等）
                    │  (fund_code) │
                    └──────┬───────┘
                           │ 外键关联
           ┌───────────────┼───────────────┐
           │               │               │
  ┌────────▼────────┐ ┌────▼────────┐ ┌────▼──────────┐
  │ fund_holdings   │ │ daily_quotes│ │ trade_records │
  │ (实时持仓)       │ │ (每日净值)  │ │ (交易记录)     │
  └────────┬────────┘ └─────┬───────┘ └───────┬───────┘
           │                │                  │
           │ Dashboard      │                  │
           │ Holdings API   │    generate_snapshots.py
           │ (实时计算)      │    (离线回放计算)
           │                │                  │
           │                ▼                  ▼
           │       ┌────────────────────────────────┐
           │       │    portfolio_snapshots          │
           │       │    (每日资产快照)                 │
           │       └────────────────┬───────────────┘
           │                        │
           ▼                        ▼
  ┌─────────────────┐    ┌──────────────────┐
  │  DashboardView  │    │   ProfitView     │
  │  (仪表盘-实时)   │    │  (收益分析-历史)  │
  └─────────────────┘    └──────────────────┘
```

**关键区别**：
- **DashboardView** 显示的是**实时数据**，由后端 JOIN `daily_quotes` 最新净值实时计算（不依赖 snapshots）
- **ProfitView** 显示的是**历史走势**，完全依赖 `portfolio_snapshots` 表的预计算数据

---

## 八、常见问题

### Q1: 快照数据和 Dashboard 的数据对不上？

正常现象。Dashboard 用最新净值实时计算（可能包含盘中波动），快照是按交易日收盘净值生成的。只有在当日收盘后运行 `generate_snapshots.py today` 后，最新快照的数据才会与 Dashboard 一致。

### Q2: 修改了一笔历史交易记录后，快照数据没变？

快照是预计算的，修改交易记录后需要重新生成：
```bash
python scripts/generate_snapshots.py    # 全量重建
```

### Q3: 某一天没有净值数据，快照会怎么处理？

该天不会生成快照。快照只在有净值数据的交易日生成。如果某只基金当天没有净值但其他基金有，该基金使用**最近一个有净值的交易日**的净值来估算市值。

### Q4: total_invested 包含已卖出基金的投入吗？

是的。`total_invested` 是**累计买入总金额，只增不减**。即使某只基金已经全部卖出，它的历史买入金额仍然计入 `total_invested`。这反映了"你总共往基金里投了多少钱"。

### Q5: 已实现收益 (realized_pnl) 是怎么算的？

每次卖出时计算：
```
这笔已实现收益 = 卖出回收金额 - 卖出份额 × 加权平均成本价
```
`realized_pnl` 是所有卖出操作的已实现收益之和（可能为负，即亏损卖出）。
