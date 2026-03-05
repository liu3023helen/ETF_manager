"""
更新支付宝黄金基金持仓到 my_holdings 表
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "etf_manager.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. 删除支付宝平台现有的黄金基金持仓
    gold_codes = ('014662', '009034', '008702', '009505', '020341')
    c.execute("DELETE FROM my_holdings WHERE platform='支付宝' AND fund_code IN (?,?,?,?,?)", gold_codes)
    print(f"Deleted {c.rowcount} old records")

    # 2. 插入新的黄金基金持仓
    # (fund_code, platform, shares, cost_price, current_value, total_invested, latest_nav, nav_date, base_shares, tradable_shares)
    holdings = [
        ('014662', '支付宝', 233.16, 2.5733, 598.57, 600.0, 2.5672, '2026-03-04', 46.63, 186.53),
        ('009034', '支付宝', 383.50, 2.5560, 1020.76, 980.0, 2.6617, '2026-03-04', 76.70, 306.80),
        ('008702', '支付宝', 479.56, 2.5023, 1197.75, 1200.0, 2.4976, '2026-03-04', 95.91, 383.65),
        ('009505', '支付宝', 416.65, 2.4001, 1007.96, 1000.0, 2.4192, '2026-03-04', 83.33, 333.32),
        ('020341', '支付宝', 311.87, 2.5652, 815.82, 800.0, 2.6159, '2026-03-04', 62.37, 249.50),
    ]

    for h in holdings:
        c.execute("""INSERT INTO my_holdings 
            (fund_code, platform, shares, cost_price, current_value, total_invested, 
             latest_nav, nav_date, base_shares, tradable_shares) 
            VALUES (?,?,?,?,?,?,?,?,?,?)""", h)
        print(f"Added: {h[0]} = {h[4]}元")

    # 3. 重排 holding_id 保持连续
    c.execute("SELECT holding_id FROM my_holdings ORDER BY fund_code, platform")
    rows = c.fetchall()
    for new_id, row in enumerate(rows, start=1):
        if row[0] != new_id:
            c.execute("UPDATE my_holdings SET holding_id=? WHERE holding_id=?", (-new_id, row[0]))
    c.execute("UPDATE my_holdings SET holding_id = -holding_id WHERE holding_id < 0")
    print(f"Reindexed {len(rows)} holdings")

    conn.commit()

    # 4. 验证结果
    print("\n=== 支付宝黄金基金持仓 ===")
    c.execute("""SELECT h.holding_id, h.fund_code, f.fund_name, h.shares, h.cost_price, 
                 h.current_value, h.latest_nav, h.nav_date 
                 FROM my_holdings h 
                 LEFT JOIN fund_info f ON h.fund_code=f.fund_code 
                 WHERE h.platform='支付宝' AND h.fund_code IN (?,?,?,?,?)
                 ORDER BY h.holding_id""", gold_codes)
    total = 0
    for row in c.fetchall():
        name = row[2][:15] if row[2] else 'N/A'
        print(f"  {row[0]}: {row[1]} {name:<15} 份额={row[3]:>7.2f} 市值={row[5]:>8.2f}")
        total += row[5]
    print(f"\n  黄金基金总市值: {total:.2f} 元")

    conn.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
