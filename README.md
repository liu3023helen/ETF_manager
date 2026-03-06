# ETF 管理系统

一个轻量级的个人基金投资管理系统，基于 FastAPI + Vue 3 构建，支持持仓管理、交易规则引擎与交易记录跟踪。

---

## 核心功能

- **持仓管理**：支持多平台（支付宝、涨乐财富通等）持仓记录，自动计算市值、盈亏与收益率，定投信息直接集成在持仓中。
- **规则引擎**：自定义交易规则（如止盈、加仓、回撤控制），基于最新净值自动生成交易信号。
- **交易记录**：统一记录交易操作和信号（买入/卖出/定投/信号），交易自动联动更新持仓数据。
- **数据可视化**：资产配置饼图、平台分布图，直观展示投资组合状态。

---

## 技术栈

### 后端
- **Python 3.10+**
- **FastAPI**：高性能 Web 框架
- **SQLite**：轻量级文件数据库
- **Pydantic**：数据校验
- **Pandas / Openpyxl**：数据处理与 Excel 交互

### 前端
- **Vue 3** + **TypeScript**
- **Vite**：构建工具
- **TDesign Vue Next**：UI 组件库
- **ECharts**：图表可视化
- **TailwindCSS**：样式框架

---

## 快速开始

### 1. 环境准备

确保已安装：
- Python 3.10 或更高版本
- Node.js 18+ (推荐使用 20+)

### 2. 安装依赖

**后端依赖：**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

**前端依赖：**
```bash
cd frontend
npm install
```

### 3. 初始化数据库

首次运行前需初始化数据库表结构：

```bash
python scripts/init_db.py
```

如需导入初始基金信息：
```bash
python scripts/init_fund_info.py
```

### 4. 启动项目

使用一键启动脚本（推荐）：
```bash
python start.py
```

或分别启动：
```bash
# 启动后端 (端口 8000)
uvicorn backend.main:app --reload

# 启动前端 (端口 5173)
cd frontend
npm run dev
```

启动后访问：
- 前端界面：http://127.0.0.1:5173
- API 文档：http://127.0.0.1:8000/docs

---

## 项目结构

```
ETF_manager/
├── backend/            # FastAPI 后端代码
│   ├── main.py         # 应用入口
│   ├── database.py     # 数据库连接
│   ├── models.py       # Pydantic 模型
│   ├── routers/        # API 路由模块
│   │   ├── dashboard.py      # 仪表盘统计
│   │   ├── holdings.py       # 持仓管理
│   │   ├── rules.py          # 交易规则
│   │   ├── trade_records.py  # 交易记录
│   │   ├── tables.py         # 通用表格查询
│   │   ├── funds.py          # 基金信息
│   │   └── quotes.py         # 每日净值
│   └── services/       # 业务逻辑层
│       └── holding_service.py
├── frontend/           # Vue 前端代码
│   ├── src/
│   │   ├── views/      # 页面组件
│   │   ├── components/ # 通用组件
│   │   ├── api/        # API 请求封装
│   │   └── router/     # 路由配置
│   └── package.json
├── data/               # 数据存储目录
│   ├── etf_manager.db  # SQLite 数据库
│   ├── 数据库表结构.md  # 详细表结构文档
│   └── 交易规则.md      # 规则配置文档
├── scripts/            # 工具脚本
│   ├── init_db.py      # 初始化数据库
│   └── verify_db.py    # 数据校验
├── start.py            # 一键启动脚本
├── requirements.txt    # Python 依赖
└── README.md           # 项目说明
```

---

## 核心数据模型

系统共包含 5 张核心表：

1. **fund_info**：基金基本信息（代码、名称、分类、风险等级）
2. **fund_holdings**：持仓记录（份额、成本、市值、盈亏、定投配置）
3. **daily_quotes**：每日净值数据
4. **trading_rules**：交易规则配置
5. **trade_records**：交易记录（合并了交易流水与交易信号）

> 详细字段说明请参考 [`data/数据库表结构.md`](data/数据库表结构.md)

---

## 使用流程

1. **录入基金信息**：在"基金信息"页面添加关注的基金代码。
2. **设置交易规则**：在"交易规则"页面配置止盈、加仓等策略。
3. **更新持仓数据**：通过"持仓管理"录入当前持有份额与成本。
4. **更新每日净值**：系统根据净值自动计算市值，并触发规则生成信号。
5. **查看交易记录**：在"交易记录"页面查看系统建议的买卖操作和历史交易。

---

## 关键计算逻辑

### 持仓市值与盈亏
```
持仓市值 = 持有份额 × 当前净值
持仓盈亏 = 持仓市值 - 累计投入
收益率 = (持仓市值 - 累计投入) ÷ 累计投入 × 100%
```

### 交易成本计算
```
买入后均价 = (原份额 × 原成本 + 买入份额 × 买入净值) ÷ (原份额 + 买入份额)
卖出后投入 = 原投入 × (1 - 卖出份额 ÷ 原份额)
```

---

## 最近更新

- **2026-03-07**：
  - 重构 `fund_holdings` 表，新增市值、盈亏、定投配置等字段，定投信息从独立表整合到持仓表。
  - 合并 `transactions`（交易流水）和 `trade_signals`（交易信号）为统一的 `trade_records` 表。
  - 删除 `dca_plans`、`transactions`、`trade_signals` 三张旧表。
  - 优化后端持仓计算逻辑，支持实时更新盈亏与收益率。
  - 清理废弃脚本与临时文件。

---

## 注意事项

1. **数据库备份**：定期备份 `data/etf_manager.db` 文件。
2. **净值更新**：建议每日收盘后手动或通过脚本更新净值数据。
3. **规则优先级**：交易规则按优先级执行，数字越大优先级越高。

---

## 许可证

MIT License
