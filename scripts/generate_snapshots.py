"""
生成 portfolio_snapshots 每日资产快照。

用法：
  python scripts/generate_snapshots.py          # 补录所有历史 + 生成今日快照
  python scripts/generate_snapshots.py today     # 仅生成今日快照

逻辑：
  对每个交易日，遍历所有持仓基金，用当日净值 × 持仓份额 计算总市值。
  持仓份额通过 trade_records 按时间累积得出（买入加、卖出减）。
"""

import sqlite3
import os
import sys
from datetime import datetime
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

# 模块级连接变量，在 main() 中初始化
conn = None


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table(conn):
    """确保 portfolio_snapshots 表存在"""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date TEXT NOT NULL UNIQUE,
        total_assets REAL DEFAULT 0,
        total_invested REAL DEFAULT 0,
        total_pnl REAL DEFAULT 0,
        pnl_rate REAL DEFAULT 0,
        realized_pnl REAL DEFAULT 0,
        fund_count INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_date ON portfolio_snapshots(snapshot_date)")
    conn.commit()
    print("portfolio_snapshots 表已就绪")


def get_all_trade_records():
    """获取所有已执行的交易记录，按日期排序"""
    return conn.execute("""
        SELECT fund_code, record_type, record_date, amount, shares, nav
        FROM trade_records
        WHERE exec_status = '已执行'
        ORDER BY record_date ASC, record_id ASC
    """).fetchall()


def get_all_nav_data():
    """获取所有基金的净值数据，返回 {fund_code: {date: close_price}}"""
    rows = conn.execute(
        "SELECT fund_code, quote_date, close_price FROM daily_quotes ORDER BY quote_date"
    ).fetchall()
    nav_map = defaultdict(dict)
    for r in rows:
        nav_map[r['fund_code']][r['quote_date']] = r['close_price']
    return nav_map


def get_all_trading_dates():
    """获取所有交易日（有任意基金净值数据的日期）"""
    rows = conn.execute(
        "SELECT DISTINCT quote_date FROM daily_quotes ORDER BY quote_date"
    ).fetchall()
    return [r['quote_date'] for r in rows]


def compute_snapshots(start_date=None):
    """
    根据交易记录和净值数据，计算每个交易日的资产快照。
    
    核心逻辑：
    1. 遍历每个交易日
    2. 根据截至当日的交易记录，计算每只基金的持仓份额和累计投入
    3. 用当日净值 × 份额 = 当日市值
    4. 汇总得到总资产、总投入、总盈亏
    """
    trades = get_all_trade_records()
    nav_map = get_all_nav_data()
    trading_dates = get_all_trading_dates()

    if not trades:
        print("无交易记录，跳过")
        return []

    # 找到最早的交易日期
    first_trade_date = trades[0]['record_date']
    
    if start_date:
        # 只生成 start_date 之后的快照
        trading_dates = [d for d in trading_dates if d >= start_date]
    else:
        # 从首笔交易日开始
        trading_dates = [d for d in trading_dates if d >= first_trade_date]

    if not trading_dates:
        print("无需生成的交易日")
        return []

    # 预处理：按日期分组交易记录
    trades_by_date = defaultdict(list)
    for t in trades:
        trades_by_date[t['record_date']].append(t)

    # 持仓状态：{fund_code: {shares, total_bought, avg_price, realized_pnl}}
    # total_bought = 累计买入总金额（只增不减）
    holdings = defaultdict(lambda: {
        'shares': 0.0,
        'total_bought': 0.0,
        'avg_price': 0.0,
        'realized_pnl': 0.0,
    })

    snapshots = []

    # Bug2 修复：当 start_date 存在时，先回放 start_date 之前的所有交易，
    # 以构建正确的历史持仓状态
    if start_date:
        for t in trades:
            if t['record_date'] >= start_date:
                break
            code = t['fund_code']
            h = holdings[code]
            trade_shares = t['shares'] or 0
            trade_amount = t['amount'] or 0
            trade_nav = t['nav'] or 0

            if t['record_type'] in ('买入', '定投'):
                old_total = h['shares'] * h['avg_price']
                h['shares'] += trade_shares
                h['total_bought'] += trade_amount
                if h['shares'] > 0:
                    h['avg_price'] = (old_total + trade_shares * trade_nav) / h['shares']
            elif t['record_type'] == '卖出':
                if h['shares'] > 0:
                    sell_ratio = min(trade_shares / h['shares'], 1.0)
                    sell_cost = h['shares'] * h['avg_price'] * sell_ratio
                    h['realized_pnl'] += (trade_amount - sell_cost)
                    h['shares'] -= trade_shares
                    if h['shares'] <= 0:
                        h['shares'] = 0
                        h['avg_price'] = 0

    for date in trading_dates:
        # 应用截至当日的所有交易
        if date in trades_by_date:
            for t in trades_by_date[date]:
                code = t['fund_code']
                h = holdings[code]
                trade_shares = t['shares'] or 0
                trade_amount = t['amount'] or 0
                trade_nav = t['nav'] or 0

                if t['record_type'] in ('买入', '定投'):
                    # 加权平均成本
                    old_total = h['shares'] * h['avg_price']
                    h['shares'] += trade_shares
                    h['total_bought'] += trade_amount
                    if h['shares'] > 0:
                        h['avg_price'] = (old_total + trade_shares * trade_nav) / h['shares']
                elif t['record_type'] == '卖出':
                    if h['shares'] > 0:
                        sell_ratio = min(trade_shares / h['shares'], 1.0)
                        sell_cost = h['shares'] * h['avg_price'] * sell_ratio
                        h['realized_pnl'] += (trade_amount - sell_cost)
                        h['shares'] -= trade_shares
                        if h['shares'] <= 0:
                            h['shares'] = 0
                            h['avg_price'] = 0

        # 计算当日总资产
        total_assets = 0.0
        total_invested = 0.0   # 累计买入总金额
        total_cost = 0.0       # 持有成本（份额×成本价）
        total_realized = 0.0
        fund_count = 0

        for code, h in holdings.items():
            if h['shares'] <= 0:
                total_invested += h['total_bought']  # 已清仓基金也计入累计投入
                total_realized += h['realized_pnl']
                continue
            
            # 找当日净值（或最近的历史净值）
            nav = nav_map.get(code, {}).get(date)
            if nav is None:
                # 没有当日净值，往前找最近的
                fund_dates = sorted(nav_map.get(code, {}).keys())
                prev_dates = [d for d in fund_dates if d <= date]
                if prev_dates:
                    nav = nav_map[code][prev_dates[-1]]
                else:
                    nav = h['avg_price']  # 最后用成本价兜底

            market_value = h['shares'] * nav
            cost_value = h['shares'] * h['avg_price']
            total_assets += market_value
            total_cost += cost_value
            total_invested += h['total_bought']
            total_realized += h['realized_pnl']
            fund_count += 1

        # 浮动盈亏 = 市值 - 持有成本
        total_pnl = total_assets - total_cost
        pnl_rate = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        snapshots.append({
            'snapshot_date': date,
            'total_assets': round(total_assets, 2),
            'total_invested': round(total_invested, 2),
            'total_pnl': round(total_pnl, 2),
            'pnl_rate': round(pnl_rate, 2),
            'realized_pnl': round(total_realized, 2),
            'fund_count': fund_count,
        })

    return snapshots


def save_snapshots(snapshots):
    """保存快照到数据库（UPSERT）"""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    count = 0
    for s in snapshots:
        conn.execute("""
            INSERT INTO portfolio_snapshots 
                (snapshot_date, total_assets, total_invested, total_pnl, pnl_rate, realized_pnl, fund_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_date) DO UPDATE SET
                total_assets = excluded.total_assets,
                total_invested = excluded.total_invested,
                total_pnl = excluded.total_pnl,
                pnl_rate = excluded.pnl_rate,
                realized_pnl = excluded.realized_pnl,
                fund_count = excluded.fund_count,
                created_at = excluded.created_at
        """, (
            s['snapshot_date'], s['total_assets'], s['total_invested'],
            s['total_pnl'], s['pnl_rate'], s['realized_pnl'], s['fund_count'], now_str,
        ))
        count += 1
    conn.commit()
    return count


def main():
    global conn
    conn = get_connection()
    ensure_table(conn)

    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if mode == 'today':
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"生成今日快照: {today}")
        snapshots = compute_snapshots(start_date=today)
    else:
        print("补录全部历史快照...")
        snapshots = compute_snapshots()

    if not snapshots:
        print("无快照数据生成")
        conn.close()
        return

    count = save_snapshots(snapshots)
    print(f"共生成/更新 {count} 条快照")
    print(f"时间范围: {snapshots[0]['snapshot_date']} ~ {snapshots[-1]['snapshot_date']}")

    # 显示最后几天的数据
    print(f"\n最近 5 天:")
    for s in snapshots[-5:]:
        print(f"  {s['snapshot_date']}: 总资产={s['total_assets']:.2f} 投入={s['total_invested']:.2f} "
              f"盈亏={s['total_pnl']:.2f}({s['pnl_rate']:.2f}%) 基金数={s['fund_count']}")

    conn.close()


if __name__ == '__main__':
    main()
