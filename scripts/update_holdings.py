"""
根据涨乐财富通截图更新持仓数据
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "etf_manager.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("=== 开始更新持仓数据 ===")
    print()
    
    # 1. 新增基金 159530 机器人ETF易方达
    c.execute("""INSERT OR IGNORE INTO fund_info (fund_code, fund_name, fund_company, fund_type, tracking_index, risk_level, fund_category) VALUES (?, ?, ?, ?, ?, ?, ?)""", 
        ('159530', '机器人ETF易方达', '易方达基金', 'ETF', '国证机器人指数', '中高风险', '机器人'))
    print("[OK] 新增基金: 159530 机器人ETF易方达")
    
    # 2. 新增基金 159781 科创创业ETF易方达
    c.execute("""INSERT OR IGNORE INTO fund_info (fund_code, fund_name, fund_company, fund_type, tracking_index, risk_level, fund_category) VALUES (?, ?, ?, ?, ?, ?, ?)""", 
        ('159781', '科创创业ETF易方达', '易方达基金', 'ETF', '科创创业50指数', '中高风险', '科创'))
    print("[OK] 新增基金: 159781 科创创业ETF易方达")
    
    # 3. 修正 588360 的信息
    c.execute("UPDATE fund_info SET fund_name='科创芯片ETF易方达', tracking_index='科创芯片指数', fund_category='芯片' WHERE fund_code='588360'")
    print("[OK] 更新基金: 588360 更名为科创芯片ETF易方达")
    
    # 4. 删除旧的错误持仓记录（588360在涨乐财富通的记录，实际应该是159781）
    c.execute("DELETE FROM my_holdings WHERE fund_code='588360' AND platform='涨乐财富通'")
    print("[OK] 删除旧持仓: 588360 在涨乐财富通的记录")
    
    # 5. 新增 159530 持仓
    c.execute("""INSERT OR REPLACE INTO my_holdings (fund_code, platform, shares, cost_price, current_value, total_invested, first_buy_date, base_shares, tradable_shares) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ('159530', '涨乐财富通', 1500, 1.609, 2196.0, 2413.5, '2025-01-15', 300, 1200))
    print("[OK] 新增持仓: 159530 机器人ETF易方达")
    
    # 6. 新增 562500 持仓（截图中有，系统里之前没有）
    c.execute("""INSERT OR REPLACE INTO my_holdings (fund_code, platform, shares, cost_price, current_value, total_invested, first_buy_date, base_shares, tradable_shares) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ('562500', '涨乐财富通', 1600, 1.123, 1688.0, 1796.8, '2025-11-05', 320, 1280))
    print("[OK] 新增持仓: 562500 机器人ETF")
    
    # 7. 更新 159770 持仓
    c.execute("UPDATE my_holdings SET shares=1600, cost_price=1.123, current_value=1688.0, total_invested=1796.8, base_shares=320, tradable_shares=1280 WHERE fund_code='159770' AND platform='涨乐财富通'")
    print("[OK] 更新持仓: 159770 机器人ETF易方达")
    
    # 8. 新增 159781 持仓
    c.execute("""INSERT OR REPLACE INTO my_holdings (fund_code, platform, shares, cost_price, current_value, total_invested, first_buy_date, base_shares, tradable_shares) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ('159781', '涨乐财富通', 1500, 0.938, 1383.0, 1407.0, '2025-02-10', 300, 1200))
    print("[OK] 新增持仓: 159781 科创创业ETF易方达")
    
    # 9. 更新 516860 市值
    c.execute("UPDATE my_holdings SET current_value=889.8 WHERE fund_code='516860' AND platform='涨乐财富通'")
    print("[OK] 更新市值: 516860 航空航天ETF -> 889.80")
    
    # 10. 更新 159241 市值
    c.execute("UPDATE my_holdings SET current_value=906.6 WHERE fund_code='159241' AND platform='涨乐财富通'")
    print("[OK] 更新市值: 159241 航空航天ETF天弘 -> 906.60")
    
    # 11. 更新 159605 市值
    c.execute("UPDATE my_holdings SET current_value=143.4 WHERE fund_code='159605' AND platform='涨乐财富通'")
    print("[OK] 更新市值: 159605 港股通互联网ETF -> 143.40")
    
    conn.commit()
    
    # 验证
    print()
    print("=== 更新后的持仓（涨乐财富通）===")
    c.execute("""SELECT h.fund_code, f.fund_name, h.shares, h.cost_price, h.current_value 
                 FROM my_holdings h LEFT JOIN fund_info f ON h.fund_code=f.fund_code 
                 WHERE h.platform='涨乐财富通' ORDER BY h.fund_code""")
    total = 0
    for row in c.fetchall():
        name = row[1][:18] if row[1] else 'N/A'
        print(f"  {row[0]}: {name:<18} 份额={row[2]:>6}, 成本={row[3]:>6.3f}, 市值={row[4]:>9.2f}")
        total += row[4] or 0
    
    print()
    print(f"  总市值: {total:.2f} 元 (截图显示: 7206.80 元)")
    
    conn.close()
    print()
    print("=== 更新完成 ===")

if __name__ == "__main__":
    main()
