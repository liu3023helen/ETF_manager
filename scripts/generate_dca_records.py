"""
根据 fund_holdings 中 7 只定投基金，自动生成历史定投交易记录。

生成逻辑：
1. 底仓建仓：在定投开始前一次性买入底仓份额
2. 定投买入：按定投频率和金额，使用当日真实净值计算买入份额
3. 智能定投：根据近期涨跌幅动态调整每期金额（100-400元）
4. 所有记录使用 daily_quotes 中的真实 close_price 作为成交价
5. 倒推法：从持仓数据反推定投开始日期，使总投入和份额与实际吻合
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row


def get_nav_map(fund_code: str) -> dict:
    """获取基金的日期->净值映射"""
    rows = conn.execute(
        "SELECT quote_date, close_price FROM daily_quotes WHERE fund_code = ? ORDER BY quote_date",
        (fund_code,)
    ).fetchall()
    return {r['quote_date']: r['close_price'] for r in rows}


def get_trading_dates(fund_code: str) -> list:
    """获取基金有净值数据的交易日列表（升序）"""
    rows = conn.execute(
        "SELECT DISTINCT quote_date FROM daily_quotes WHERE fund_code = ? ORDER BY quote_date",
        (fund_code,)
    ).fetchall()
    return [r['quote_date'] for r in rows]


def parse_weekday(freq_str: str) -> int:
    """从定投频率描述中解析星期几 (0=周一, 6=周日)"""
    weekday_map = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6}
    for char, idx in weekday_map.items():
        if f'周{char}' in freq_str:
            return idx
    return -1  # 每天


def is_dca_day(date_str: str, freq_str: str) -> bool:
    """判断某日是否是定投日"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    if '每天' in freq_str:
        return dt.weekday() < 5  # 工作日
    target_weekday = parse_weekday(freq_str)
    return dt.weekday() == target_weekday


def calc_smart_dca_amount(nav_map: dict, date_str: str, trading_dates: list, base_amount: float = 200.0) -> float:
    """
    智能定投：根据近20日均价的偏离度动态调整金额
    - 当前净值低于均价 → 多投（最多400）
    - 当前净值高于均价 → 少投（最少100）
    """
    idx = trading_dates.index(date_str) if date_str in trading_dates else -1
    if idx < 20:
        return base_amount

    recent_dates = trading_dates[max(0, idx - 20):idx]
    recent_navs = [nav_map[d] for d in recent_dates if d in nav_map]
    if not recent_navs:
        return base_amount

    avg_nav = sum(recent_navs) / len(recent_navs)
    current_nav = nav_map.get(date_str, avg_nav)
    deviation = (current_nav - avg_nav) / avg_nav

    # 偏离度映射到金额：低于均价越多投越多
    if deviation <= -0.05:
        amount = 400.0
    elif deviation <= -0.02:
        amount = 300.0
    elif deviation <= 0.02:
        amount = 200.0
    elif deviation <= 0.05:
        amount = 150.0
    else:
        amount = 100.0

    return amount


def generate_records_for_fund(fund: dict) -> list:
    """为单只基金生成交易记录"""
    code = fund['fund_code']
    platform = fund['platform']
    nav_map = get_nav_map(code)
    trading_dates = get_trading_dates(code)

    if not trading_dates:
        print(f"  [跳过] {code}: 无净值数据")
        return []

    total_shares = fund['holding_shares']
    base_shares = fund['base_shares']
    invested_capital = fund['invested_capital']
    dca_freq = fund['dca_frequency'] or ''
    dca_amount = fund['dca_amount'] or 0
    dca_type = fund['dca_type'] or '固定金额'
    is_smart = '智能' in dca_type

    records = []

    # ===== 第一步：估算需要多少期定投来积累当前份额 =====
    # 底仓份额 = base_shares（一次性建仓）
    # 定投份额 = total_shares - base_shares
    dca_shares_target = total_shares - base_shares

    # 从最近的交易日往前倒推，找到足够的定投日
    # 先收集所有符合频率的定投日
    dca_days = []
    for d in trading_dates:
        if is_dca_day(d, dca_freq) and d in nav_map:
            dca_days.append(d)

    if not dca_days:
        print(f"  [跳过] {code}: 无符合频率的定投日")
        return []

    # 从最近往前倒推，累积份额直到达到目标
    accumulated_shares = 0.0
    accumulated_invested = 0.0
    selected_dca_days = []

    for d in reversed(dca_days):
        nav = nav_map[d]
        if nav <= 0:
            continue

        if is_smart:
            amount = calc_smart_dca_amount(nav_map, d, trading_dates)
        else:
            amount = dca_amount

        shares_bought = round(amount / nav, 2)
        accumulated_shares += shares_bought
        accumulated_invested += amount
        selected_dca_days.append((d, amount, shares_bought, nav))

        if accumulated_shares >= dca_shares_target:
            break

    # 按日期正序排列
    selected_dca_days.reverse()

    # ===== 第二步：生成底仓建仓记录 =====
    if selected_dca_days:
        # 底仓建仓日期：定投开始前一个交易日
        first_dca_date = selected_dca_days[0][0]
        first_dca_idx = trading_dates.index(first_dca_date) if first_dca_date in trading_dates else 0
        base_date = trading_dates[max(0, first_dca_idx - 1)]
    else:
        base_date = trading_dates[-1]

    base_nav = nav_map.get(base_date, fund['avg_buy_price'])
    base_amount = round(base_shares * base_nav, 2)

    records.append({
        'fund_code': code,
        'record_type': '买入',
        'record_date': base_date,
        'signal_type': '底仓建仓',
        'trigger_condition': '初始建仓',
        'trigger_value': base_nav,
        'suggested_action': 'BUY',
        'exec_status': '已执行',
        'exec_date': base_date,
        'actual_action': 'BUY',
        'platform': platform,
        'amount': base_amount,
        'shares': base_shares,
        'nav': base_nav,
        'fee': 0.0,
        'note': '底仓建仓',
    })

    # ===== 第三步：生成定投买入记录 =====
    for d, amount, shares_bought, nav in selected_dca_days:
        signal = '智能定投' if is_smart else '定投'
        condition = f'{dca_freq}' if dca_freq else '定投日'

        records.append({
            'fund_code': code,
            'record_type': '买入',
            'record_date': d,
            'signal_type': signal,
            'trigger_condition': condition,
            'trigger_value': nav,
            'suggested_action': 'BUY',
            'exec_status': '已执行',
            'exec_date': d,
            'actual_action': 'BUY',
            'platform': platform,
            'amount': round(amount, 2),
            'shares': shares_bought,
            'nav': nav,
            'fee': 0.0,
            'note': f'定投买入 {amount:.0f}元',
        })

    return records


def main():
    # 获取7只定投基金
    funds = conn.execute("""
        SELECT h.*, f.fund_name, f.fund_category
        FROM fund_holdings h
        LEFT JOIN fund_info f ON h.fund_code = f.fund_code
        WHERE h.dca_is_active = 1
        ORDER BY h.fund_code
    """).fetchall()

    print(f"找到 {len(funds)} 只定投基金\n")

    all_records = []
    for fund in funds:
        f = dict(fund)
        print(f"处理: {f['fund_code']} {f['fund_name']}")
        print(f"  目标: 总份额={f['holding_shares']} 底仓={f['base_shares']} 定投份额={f['holding_shares'] - f['base_shares']}")
        print(f"  定投: {f['dca_frequency']} 每期{f['dca_amount']}元 类型={f['dca_type']}")

        records = generate_records_for_fund(f)
        all_records.extend(records)

        base_count = sum(1 for r in records if r['signal_type'] == '底仓建仓')
        dca_count = len(records) - base_count
        total_amount = sum(r['amount'] for r in records)
        total_shares = sum(r['shares'] for r in records)
        print(f"  生成: {base_count}笔建仓 + {dca_count}笔定投 = {len(records)}条记录")
        print(f"  累计: 投入{total_amount:.2f}元 份额{total_shares:.2f}份")
        if records:
            print(f"  时间: {records[0]['record_date']} ~ {records[-1]['record_date']}")
        print()

    print(f"共生成 {len(all_records)} 条交易记录")

    # 清除这7只基金的旧交易记录（保留其他基金的记录）
    dca_codes = [dict(f)['fund_code'] for f in funds]
    placeholders = ','.join(['?'] * len(dca_codes))
    deleted = conn.execute(
        f"DELETE FROM trade_records WHERE fund_code IN ({placeholders})",
        dca_codes
    ).rowcount
    print(f"已清除旧记录: {deleted}条")

    # 插入新记录
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for r in all_records:
        conn.execute("""
            INSERT INTO trade_records (
                fund_code, record_type, record_date, signal_type,
                trigger_condition, trigger_value, suggested_action,
                exec_status, exec_date, actual_action,
                platform, amount, shares, nav, fee, note, created_at
            ) VALUES (
                :fund_code, :record_type, :record_date, :signal_type,
                :trigger_condition, :trigger_value, :suggested_action,
                :exec_status, :exec_date, :actual_action,
                :platform, :amount, :shares, :nav, :fee, :note, :created_at
            )
        """, {**r, 'created_at': now_str})

    conn.commit()

    # 验证
    total = conn.execute("SELECT COUNT(*) FROM trade_records").fetchone()[0]
    print(f"\n插入成功! 当前 trade_records 共 {total} 条记录")

    # 更新 fund_holdings 的 first_buy_date
    for fund in funds:
        f = dict(fund)
        first = conn.execute(
            "SELECT MIN(record_date) FROM trade_records WHERE fund_code = ?",
            (f['fund_code'],)
        ).fetchone()[0]
        if first:
            conn.execute(
                "UPDATE fund_holdings SET first_buy_date = ? WHERE fund_code = ?",
                (first, f['fund_code'])
            )
    conn.commit()
    print("已更新 first_buy_date 字段")

    conn.close()


if __name__ == '__main__':
    main()
