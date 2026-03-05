"""
更新 fund_info 和 my_holdings：
1. 修正错误的基金名称
2. 添加缺失的联接基金
3. 更新支付宝持仓数据
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "etf_manager.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. 修正 fund_info 中的错误名称
    corrections = [
        ("005693", "广发中证军工ETF联接C", "广发基金", "ETF联接", "中证军工指数", "中高风险", "军工"),
        ("014662", "天弘上海金ETF联接C", "天弘基金", "ETF联接", "上海金", "中风险", "黄金"),
        ("159770", "天弘中证机器人ETF", "天弘基金", "ETF", "中证机器人指数", "中高风险", "机器人"),
        ("159605", "广发中证海外中国互联网30ETF", "广发基金", "ETF", "中证海外中国互联网30", "中高风险", "互联网"),
    ]
    
    for code, name, company, ftype, index, risk, category in corrections:
        c.execute("""UPDATE fund_info SET 
            fund_name=?, fund_company=?, fund_type=?, tracking_index=?, risk_level=?, fund_category=?
            WHERE fund_code=?""", (name, company, ftype, index, risk, category, code))
        print(f"Updated: {code} -> {name}")

    # 2. 添加缺失的联接基金（如果不存在）
    new_funds = [
        ("020482", "招商中证机器人ETF联接C", "招商基金", "ETF联接", "中证机器人指数", "中高风险", "机器人"),
        ("018345", "华夏中证机器人ETF联接C", "华夏基金", "ETF联接", "中证机器人指数", "中高风险", "机器人"),
        ("014881", "天弘中证机器人ETF联接C", "天弘基金", "ETF联接", "中证机器人指数", "中高风险", "机器人"),
    ]
    
    for fund in new_funds:
        c.execute("SELECT 1 FROM fund_info WHERE fund_code=?", (fund[0],))
        if not c.fetchone():
            c.execute("INSERT INTO fund_info (fund_code, fund_name, fund_company, fund_type, tracking_index, risk_level, fund_category) VALUES (?,?,?,?,?,?,?)", fund)
            print(f"Added: {fund[0]} {fund[1]}")
        else:
            print(f"Exists: {fund[0]}")

    conn.commit()

    # 3. 删除支付宝平台错误的旧持仓（562500等ETF代码）
    old_codes = ("562500",)
    c.execute("DELETE FROM my_holdings WHERE platform='支付宝' AND fund_code IN (?)", old_codes)
    print(f"\nDeleted {c.rowcount} old holdings")

    # 4. 插入支付宝基金持仓（联接基金）
    # (fund_code, platform, shares, cost_price, current_value, total_invested, latest_nav, nav_date, base_shares, tradable_shares)
    holdings = [
        ("005693", "支付宝", 330.17, 1.4235, 571.25, 470.0, 1.4273, "2026-03-04", 66.03, 264.14),
        ("017470", "支付宝", 433.92, 2.1663, 893.79, 940.0, 2.0598, "2026-03-04", 86.78, 347.14),
        ("020482", "支付宝", 1209.85, 1.6531, 1863.17, 2000.0, 1.5400, "2026-03-04", 241.97, 967.88),
        ("018345", "支付宝", 1545.12, 1.2944, 1863.57, 2000.0, 1.2061, "2026-03-04", 309.02, 1236.10),
        ("014881", "支付宝", 1572.57, 1.2718, 1862.87, 2000.0, 1.1846, "2026-03-04", 314.51, 1258.06),
    ]

    for h in holdings:
        # 先删除已存在的
        c.execute("DELETE FROM my_holdings WHERE fund_code=? AND platform=?", (h[0], h[1]))
        c.execute("""INSERT INTO my_holdings 
            (fund_code, platform, shares, cost_price, current_value, total_invested, 
             latest_nav, nav_date, base_shares, tradable_shares) 
            VALUES (?,?,?,?,?,?,?,?,?,?)""", h)
        print(f"Added holding: {h[0]} = {h[4]}元")

    conn.commit()

    # 5. 重排 holding_id
    c.execute("SELECT holding_id FROM my_holdings ORDER BY fund_code, platform")
    rows = c.fetchall()
    for new_id, row in enumerate(rows, start=1):
        if row[0] != new_id:
            c.execute("UPDATE my_holdings SET holding_id=? WHERE holding_id=?", (-new_id, row[0]))
    c.execute("UPDATE my_holdings SET holding_id = -holding_id WHERE holding_id < 0")
    print(f"\nReindexed {len(rows)} holdings")

    conn.commit()

    # 6. 验证结果
    print("\n=== 支付宝基金持仓 ===")
    c.execute("""SELECT h.holding_id, h.fund_code, f.fund_name, h.shares, h.cost_price, 
                 h.current_value, h.latest_nav 
                 FROM my_holdings h 
                 LEFT JOIN fund_info f ON h.fund_code=f.fund_code 
                 WHERE h.platform='支付宝' 
                 ORDER BY h.holding_id""")
    total = 0
    for row in c.fetchall():
        name = row[2][:18] if row[2] else 'N/A'
        print(f"  {row[0]}: {row[1]} {name:<18} 份额={row[3]:>8.2f} 市值={row[5]:>8.2f}")
        total += row[5]
    print(f"\n  支付宝基金总市值: {total:.2f} 元")

    conn.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
