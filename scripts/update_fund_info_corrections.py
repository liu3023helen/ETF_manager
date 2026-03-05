"""
根据核查报告更新 fund_info 表中的错误数据
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "etf_manager.db")

def update_corrections():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    
    # 1. 高优先级：成立日期错误的基金
    updates.append(("2022-12-07", "+106.87%", "+107.37%", "017470"))  # 嘉实上证科创板芯片ETF联接C
    updates.append(("2023-05-31", "+29.84%", "-", "018345"))  # 华夏中证机器人ETF联接C
    
    # 2. 高优先级：成立以来收益率偏差>10%的基金
    updates.append(("2024-01-10", "+60.15%", "+23.11%", "159530"))  # 易方达国证机器人产业ETF
    updates.append(("2021-10-26", "+11.94%", "+21.36%", "159770"))  # 天弘中证机器人ETF
    updates.append(("2021-06-28", "-5.67%", "+54.94%", "159781"))  # 易方达中证科创创业50ETF
    updates.append(("2025-05-21", "+60%", "-", "159241"))  # 天弘国证航天航空行业ETF
    
    # 3. 中优先级：黄金基金收益率更新
    updates.append(("2020-07-16", "+159.31%", "+75.04%", "008702"))  # 华夏黄金ETF联接C
    
    # 4. 其他需要更新的基金
    updates.append(("2022-03-02", "+155.87%", "+65.35%", "014662"))  # 天弘上海金ETF联接C
    updates.append(("2023-07-11", "+24.90%", "+11.39%", "014881"))  # 天弘中证机器人ETF联接C
    
    # 执行更新
    for inception_date, return_si, return_1y, fund_code in updates:
        if return_1y == "-":
            cursor.execute('''
                UPDATE fund_info 
                SET inception_date = ?, return_since_inception = ?, updated_at = datetime('now', 'localtime')
                WHERE fund_code = ?
            ''', (inception_date, return_si, fund_code))
        else:
            cursor.execute('''
                UPDATE fund_info 
                SET inception_date = ?, return_since_inception = ?, return_1y = ?, updated_at = datetime('now', 'localtime')
                WHERE fund_code = ?
            ''', (inception_date, return_si, return_1y, fund_code))
        
        print(f"已更新 {fund_code}: 成立日期={inception_date}, 成立以来={return_si}, 近1年={return_1y}")
    
    conn.commit()
    
    # 验证更新结果
    print("\n=== 更新验证 ===")
    cursor.execute('''
        SELECT fund_code, fund_name, inception_date, return_since_inception, return_1y 
        FROM fund_info 
        WHERE fund_code IN ('017470', '018345', '159530', '159770', '159781', '159241', '008702', '014662', '014881')
        ORDER BY fund_code
    ''')
    
    for row in cursor.fetchall():
        print(f"{row[0]} | {row[1][:20]:20} | 成立={row[2]} | 成立以来={row[3]:8} | 近1年={row[4]}")
    
    conn.close()
    print("\n[OK] 所有更新已完成")

if __name__ == '__main__':
    update_corrections()
