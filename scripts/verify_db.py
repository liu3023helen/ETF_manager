"""
ETF管理系统 - 数据验证脚本
查询各表数据并格式化输出，验证数据完整性
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


def verify():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ===== 1. 基金基本信息 =====
    print("=" * 80)
    print("1. 基金基本信息 (fund_info)")
    print("=" * 80)
    cursor.execute("SELECT * FROM fund_info ORDER BY fund_category, fund_code;")
    for row in cursor.fetchall():
        print(f"  [{row['fund_category']}] {row['fund_name']}")
        print(f"    代码: {row['fund_code']}  公司: {row['fund_company']}  类型: {row['fund_type']}  风险: {row['risk_level']}")
        if row['return_1y']:
            print(f"    收益率: 近1年={row['return_1y']}  近3年={row['return_3y']}  成立以来={row['return_since_inception']}")
        print()

    # ===== 2. 持仓管理 =====
    print("=" * 80)
    print("2. 持仓管理 (fund_holdings)")
    print("=" * 80)
    cursor.execute("""
        SELECT h.*, f.fund_name, f.fund_category
        FROM fund_holdings h
        LEFT JOIN fund_info f ON h.fund_code = f.fund_code
        ORDER BY h.platform, f.fund_category;
    """)
    current_platform = None
    for row in cursor.fetchall():
        if row['platform'] != current_platform:
            current_platform = row['platform']
            print(f"\n  --- {current_platform} ---")
        print(f"  {row['fund_name']} ({row['fund_code']})")
        print(f"    份额: {row['holding_shares']}  均价: {row['avg_buy_price']}  市值: {row['holding_value']}  盈亏: {row['profit_loss_amount']}  收益率: {row['return_rate']}%")
        if row['dca_is_active']:
            print(f"    定投: {row['dca_frequency']}  金额: {row['dca_amount']}  类型: {row['dca_type']}  累计: {row['dca_total_invested']}")

    # ===== 3. 每日净值 =====
    print(f"\n{'=' * 80}")
    print("3. 每日净值快照 (daily_quotes)")
    print("=" * 80)
    cursor.execute("""
        SELECT COUNT(*) as cnt, MIN(quote_date) as min_date, MAX(quote_date) as max_date
        FROM daily_quotes;
    """)
    row = cursor.fetchone()
    print(f"  共 {row['cnt']} 条记录")
    if row['cnt'] > 0:
        print(f"  日期范围: {row['min_date']} ~ {row['max_date']}")
        # 显示最近10条
        cursor.execute("""
            SELECT q.fund_code, q.quote_date, q.close_price
            FROM daily_quotes q
            ORDER BY q.quote_date DESC, q.fund_code LIMIT 10;
        """)
        for r in cursor.fetchall():
            print(f"  [{r['quote_date']}] {r['fund_code']}: 净值={r['close_price']}")

    # ===== 4. 交易规则 =====
    print(f"\n{'=' * 80}")
    print("4. 交易规则 (trading_rules)")
    print("=" * 80)
    cursor.execute("SELECT * FROM trading_rules ORDER BY fund_category, rule_type, priority;")
    current_type = None
    for row in cursor.fetchall():
        key = f"{row['fund_category']}-{row['rule_type']}"
        if key != current_type:
            current_type = key
            print(f"\n  --- {row['fund_category']} / {row['rule_type']} ---")
        status = "ON" if row['is_active'] else "OFF"
        print(f"  [{status}] P{row['priority']}: {row['condition_desc']} -> {row['action_desc']}")

    # ===== 5. 交易记录 =====
    print(f"\n{'=' * 80}")
    print("5. 交易记录 (trade_records)")
    print("=" * 80)
    cursor.execute("""
        SELECT t.*, f.fund_name
        FROM trade_records t
        LEFT JOIN fund_info f ON t.fund_code = f.fund_code
        ORDER BY t.record_date DESC, t.record_id DESC LIMIT 20;
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            fund_name = row['fund_name'] or row['fund_code']
            print(f"  [{row['record_date']}] {fund_name} | {row['record_type']} | {row['exec_status']} | 金额={row['amount']} 份额={row['shares']}")
    else:
        print("  暂无交易记录")

    # ===== 6. 资产快照 =====
    print(f"\n{'=' * 80}")
    print("6. 资产快照 (portfolio_snapshots)")
    print("=" * 80)
    try:
        cursor.execute("SELECT COUNT(*) as cnt FROM portfolio_snapshots;")
        cnt = cursor.fetchone()['cnt']
        print(f"  共 {cnt} 条快照记录")
        if cnt > 0:
            cursor.execute("SELECT * FROM portfolio_snapshots ORDER BY snapshot_date DESC LIMIT 5;")
            for row in cursor.fetchall():
                print(f"  [{row['snapshot_date']}] 总资产={row['total_assets']}  投入={row['total_invested']}  盈亏={row['total_pnl']}({row['pnl_rate']}%)  基金数={row['fund_count']}")
    except sqlite3.OperationalError:
        print("  portfolio_snapshots 表不存在")

    # ===== 7. 统计总结 =====
    print(f"\n{'=' * 80}")
    print("7. 数据统计")
    print("=" * 80)
    tables = ["fund_info", "fund_holdings", "daily_quotes", "trading_rules", "trade_records", "portfolio_snapshots"]
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM [{table}];")
            count = cursor.fetchone()[0]
            print(f"  {table:25s}: {count:>6d} 条")
        except sqlite3.OperationalError:
            print(f"  {table:25s}: 表不存在")

    conn.close()
    print("\n验证完成!")


if __name__ == "__main__":
    verify()
