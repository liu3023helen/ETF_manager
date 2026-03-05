"""
重建 my_holdings 表：
1. 清空现有数据
2. 插入最新截图提取的17条持仓数据
3. holding_id 按 fund_code 排序从1开始连续编号
4. fund_name 从 fund_info 表获取
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


# 最新持仓数据（按 fund_code 排序）
# (fund_code, platform, shares, cost_price, total_invested, first_buy_date)
HOLDINGS_DATA = [
    # 1. 002183 广发天天红货币B - 涨乐财富通
    ("002183", "涨乐财富通", 81064.63, 1.0, 81064.63, None),
    # 2. 005693 广发中证军工ETF联接C - 支付宝 (含待确认100元, total_invested=571.25)
    ("005693", "支付宝", 330.17, 1.4235, 571.25, None),
    # 3. 008702 华夏黄金ETF联接C - 支付宝
    ("008702", "支付宝", 479.56, 2.5023, 1200.00, None),
    # 4. 009034 建信上海金ETF联接C - 支付宝
    ("009034", "支付宝", 383.50, 2.5560, 980.22, None),
    # 5. 009505 富国上海金ETF联接C - 支付宝
    ("009505", "支付宝", 416.65, 2.4001, 999.96, None),
    # 6. 014662 天弘上海金ETF联接C - 支付宝
    ("014662", "支付宝", 233.16, 2.5733, 600.00, None),
    # 7. 014881 天弘中证机器人ETF联接C - 支付宝
    ("014881", "支付宝", 1572.57, 1.2718, 2000.00, None),
    # 8. 017470 嘉实上证科创板芯片ETF联接C - 支付宝
    ("017470", "支付宝", 433.92, 2.1663, 940.00, None),
    # 9. 018345 华夏中证机器人ETF联接C - 支付宝
    ("018345", "支付宝", 1545.12, 1.2944, 2000.00, None),
    # 10. 020341 工银瑞信黄金ETF联接E - 支付宝 (含待确认200元, total_invested=shares*cost+200≈1000)
    ("020341", "支付宝", 311.87, 2.5652, 1000.00, None),
    # 11. 020482 招商中证机器人ETF联接C - 支付宝
    ("020482", "支付宝", 1209.85, 1.6531, 2000.00, None),
    # 12. 159227 华夏国证航天航空行业ETF - 涨乐财富通
    ("159227", "涨乐财富通", 600, 1.506, 903.60, None),
    # 13. 159241 天弘国证航天航空行业ETF - 涨乐财富通
    ("159241", "涨乐财富通", 600, 1.538, 922.80, None),
    # 14. 159530 易方达国证机器人产业ETF - 涨乐财富通
    ("159530", "涨乐财富通", 1500, 1.609, 2413.50, None),
    # 15. 159770 天弘中证机器人ETF - 涨乐财富通
    ("159770", "涨乐财富通", 1600, 1.123, 1796.80, None),
    # 16. 159781 易方达中证科创创业50ETF - 涨乐财富通
    ("159781", "涨乐财富通", 1500, 0.938, 1407.00, None),
    # 17. 159792 富国中证港股通互联网ETF - 涨乐财富通
    ("159792", "涨乐财富通", 200, 0.786, 157.20, None),
]


def rebuild_holdings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 从 fund_info 获取 fund_name 映射
    cursor.execute("SELECT fund_code, fund_name FROM fund_info")
    name_map = {row[0]: row[1] for row in cursor.fetchall()}

    # 2. 清空现有数据
    cursor.execute("DELETE FROM my_holdings")
    print(f"已清空 my_holdings 表")

    # 3. 构建插入数据：holding_id 从1开始，base_shares = shares * 0.2
    insert_data = []
    for i, (fund_code, platform, shares, cost_price, total_invested, first_buy_date) in enumerate(HOLDINGS_DATA, start=1):
        fund_name = name_map.get(fund_code, None)
        base_shares = round(shares * 0.2, 2)
        tradable_shares = round(shares - base_shares, 2)
        insert_data.append((
            i, fund_code, fund_name, platform,
            shares, cost_price, base_shares, tradable_shares,
            total_invested, first_buy_date
        ))

    # 4. 插入数据
    cursor.executemany("""
        INSERT INTO my_holdings (holding_id, fund_code, fund_name, platform, shares, cost_price, base_shares, tradable_shares, total_invested, first_buy_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_data)

    conn.commit()
    print(f"已插入 {len(insert_data)} 条记录\n")

    # 5. 验证结果
    cursor.execute("SELECT * FROM my_holdings ORDER BY holding_id;")
    rows = cursor.fetchall()
    print(f"{'ID':>3} {'代码':<8} {'名称':<24} {'平台':<10} {'份额':>12} {'成本价':>8} {'底仓':>10} {'可交易':>12} {'累计投入':>10}")
    print("-" * 110)
    for row in rows:
        name = row[2] or ""
        print(f"{row[0]:>3} {row[1]:<8} {name:<24} {row[3]:<10} {row[4]:>12.2f} {row[5]:>8.4f} {row[6]:>10.2f} {row[7]:>12.2f} {row[8]:>10.2f}")

    conn.close()
    print(f"\n重建完成! 共 {len(rows)} 条记录")


if __name__ == "__main__":
    rebuild_holdings()
