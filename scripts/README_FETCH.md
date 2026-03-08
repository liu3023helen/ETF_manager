# ETF净值爬取工具（完全免费）

## 概述
自动获取持仓ETF的每日净值，写入数据库。支持 AkShare 和新浪双数据源。

## 使用方式

### 方式一：手动运行（测试用）

```bash
# 获取今日所有持仓基金的净值
python scripts/fetch_daily_quotes.py

# 获取某基金历史数据（补数据用）
python scripts/fetch_daily_quotes.py --history 159770 --days 60

# 强制更新（覆盖已有数据）
python scripts/fetch_daily_quotes.py --force
```

### 方式二：Windows定时任务（推荐）

1. 打开「任务计划程序」
2. 创建基本任务 → 名称：`ETF净值更新`
3. 触发器：每天 21:00
4. 操作：启动程序
5. 程序：`scripts/run_fetch.bat`
6. 起始于：`E:\LXY_learn\ETF_manager`（你的项目路径）

### 方式三：GitHub Actions（云端免费）

1. 将代码推送到 GitHub 仓库
2. 自动在 `.github/workflows/fetch-quotes.yml` 配置的定时任务运行
3. 免费额度：每月 2000 分钟
4. 运行记录可在 Actions 标签页查看

## 数据源优先级

1. **AkShare**（东方财富）- 首选，数据完整
2. **新浪接口** - 备用，实时性好

## 日志查看

日志保存在 `log/fetch_quotes.log`

```bash
tail -f log/fetch_quotes.log
```

## 常见问题

**Q: 为什么有些基金获取不到数据？**  
A: 检查基金代码是否正确，或者该ETF是否刚上市数据不全。

**Q: 什么时候运行最合适？**  
A: ETF净值通常在 19:00-21:00 之间更新，建议定时在 21:30 之后运行。

**Q: 非交易日会获取数据吗？**  
A: 脚本会尝试获取，但非交易日数据源可能返回空数据或最后交易日的数据。
