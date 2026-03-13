import sqlite3
import os
import random
from datetime import datetime, timedelta

db_path = os.path.join(os.path.dirname(__file__), 'data', 'etf_manager.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 1. 检查 schema
print("--- trade_records schema ---")
for row in conn.execute("PRAGMA table_info(trade_records)"):
    print(dict(row))

# 2. 获取基金和持仓
funds = conn.execute("SELECT h.fund_code, f.fund_name, h.holding_shares, h.avg_buy_price FROM fund_holdings h JOIN fund_info f ON h.fund_code = f.fund_code").fetchall()

# 3. 构造交易记录
records = []
now = datetime.now()

for fund in funds:
    code = fund['fund_code']
    shares = fund['holding_shares']
    price = fund['avg_buy_price']
    
    if not shares or shares <= 0:
        continue
        
    # 模拟 3-5 笔历史交易构成当前持仓
    num_trades = random.randint(3, 5)
    shares_per_trade = round(shares / num_trades, 2)
    
    for i in range(num_trades):
        # 过去 1-180 天内的随机日期
        days_ago = random.randint(1, 180)
        trade_date = (now - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 价格在成本价附近波动
        trade_price = round(price * random.uniform(0.9, 1.1), 4)
        trade_amount = round(shares_per_trade * trade_price, 2)
        fee = round(trade_amount * 0.0005, 2) # 0.05% 手续费
        if fee < 5: fee = 5.0 # 最低5元（针对某些场外基金可能是0，场内是万0.5免五等，这里简化）
        
        records.append({
            'fund_code': code,
            'record_type': '历史导入',
            'record_date': trade_date,
            'signal_type': '网格买入' if random.random() > 0.3 else '定投',
            'trigger_condition': '价格跌破网格线' if random.random() > 0.3 else '到达定投日',
            'trigger_value': trade_price,
            'suggested_action': 'BUY',
            'exec_status': '已执行',
            'exec_date': trade_date,
            'actual_action': 'BUY',
            'nav': trade_price,
            'shares': shares_per_trade,
            'amount': trade_amount,
            'fee': fee,
            'note': '模拟测试数据'
        })

print(f"Generating {len(records)} test records...")

# 插入数据
try:
    conn.execute("DELETE FROM trade_records WHERE note = '模拟测试数据'") # 清理之前的模拟数据
    
    for r in records:
        conn.execute("""
            INSERT INTO trade_records (
                fund_code, record_type, record_date, signal_type, 
                trigger_condition, trigger_value, suggested_action, 
                exec_status, exec_date, actual_action, 
                nav, shares, amount, fee, note
            ) VALUES (
                :fund_code, :record_type, :record_date, :signal_type,
                :trigger_condition, :trigger_value, :suggested_action,
                :exec_status, :exec_date, :actual_action,
                :nav, :shares, :amount, :fee, :note
            )
        """, r)
    conn.commit()
    print("Success! Inserted simulated trade records.")
except Exception as e:
    print(f"Error inserting: {e}")

conn.close()
