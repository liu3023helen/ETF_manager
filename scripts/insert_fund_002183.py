"""插入广发天天红货币B基金信息"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "etf_manager.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('''
INSERT INTO fund_info (fund_code, fund_name, fund_company, fund_type, tracking_index, risk_level, fund_category, top_holdings, risk_points, return_1y, return_3y, return_since_inception)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', ('002183', '广发天天红货币B', '广发基金管理有限公司', '货币型', None, '低风险', '货币基金', '22国开14(1.26%)、24建设银行CD104(1.02%)、23国开14(0.67%)、24民生银行CD230(0.66%)、24民生银行CD306(0.58%)', '低风险，流动性强', '1.43%', '5.52%', '29.77%'))

conn.commit()
print('插入成功!')

# 验证
cursor.execute('SELECT * FROM fund_info WHERE fund_code = "002183"')
row = cursor.fetchone()
cols = [desc[0] for desc in cursor.description]
for col, val in zip(cols, row):
    print(f'{col}: {val}')

conn.close()
