"""
ETF管理系统 - 数据验证脚本
查询各表数据并格式化输出，验证数据完整性
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "etf_manager.db")


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
        print(f"    重仓: {row['top_holdings']}")
        print()

    # ===== 2. 持仓管理 =====
    print("=" * 80)
    print("2. 持仓管理 (my_holdings)")
    print("=" * 80)
    cursor.execute("""
        SELECT h.*, f.fund_name, f.fund_category
        FROM my_holdings h
        JOIN fund_info f ON h.fund_code = f.fund_code
        ORDER BY h.platform, f.fund_category;
    """)
    current_platform = None
    for row in cursor.fetchall():
        if row['platform'] != current_platform:
            current_platform = row['platform']
            print(f"\n  --- {current_platform} ---")
        print(f"  {row['fund_name']}")
        print(f"    份额: {row['shares']}  成本: {row['cost_price']}  市值: {row['current_value']}")
        print(f"    底仓: {row['base_shares']}  可交易: {row['tradable_shares']}  累计投入: {row['total_invested']}")

    # ===== 3. 每日净值 =====
    print(f"\n{'=' * 80}")
    print("3. 每日净值快照 (daily_quotes)")
    print("=" * 80)
    cursor.execute("""
        SELECT q.*, f.fund_name
        FROM daily_quotes q
        JOIN fund_info f ON q.fund_code = f.fund_code
        ORDER BY q.date DESC, q.fund_code;
    """)
    for row in cursor.fetchall():
        print(f"  [{row['date']}] {row['fund_name']}: 净值={row['nav']}  涨跌={row['daily_change_pct']}%  盈亏={row['daily_pnl']}")

    # ===== 4. 定投计划 =====
    print(f"\n{'=' * 80}")
    print("4. 定投计划 (dca_plans)")
    print("=" * 80)
    cursor.execute("""
        SELECT d.*, f.fund_name
        FROM dca_plans d
        JOIN fund_info f ON d.fund_code = f.fund_code
        ORDER BY d.platform;
    """)
    for row in cursor.fetchall():
        status = "启用" if row['is_active'] else "停用"
        print(f"  [{status}] {row['fund_name']} ({row['platform']})")
        print(f"    频率: {row['frequency']}  金额: {row['amount']}  类型: {row['dca_type']}  累计: {row['total_invested']}")

    # ===== 5. 交易规则 =====
    print(f"\n{'=' * 80}")
    print("5. 交易规则 (trading_rules)")
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

    # ===== 6. 统计总结 =====
    print(f"\n{'=' * 80}")
    print("6. 数据统计")
    print("=" * 80)
    tables = ["fund_info", "my_holdings", "daily_quotes", "dca_plans", "transactions", "trading_rules", "trade_signals"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"  {table:20s}: {count:>4d} 条")

    conn.close()
    print("\n验证完成!")


if __name__ == "__main__":
    verify()
