"""
持仓 Service 层
封装 fund_holdings 的增删改查业务逻辑，供 Router 调用
"""
import sqlite3
from datetime import datetime


def get_holding(db: sqlite3.Connection, fund_code: str, platform: str):
    """根据基金代码+平台获取持仓记录"""
    row = db.execute(
        "SELECT * FROM fund_holdings WHERE fund_code=? AND platform=?",
        (fund_code, platform),
    ).fetchone()
    return dict(row) if row else None


def apply_transaction(db: sqlite3.Connection, tx_type: str, fund_code: str,
                      platform: str, amount: float, shares: float,
                      nav_at_tx: float = None):
    """
    根据交易类型更新 fund_holdings
    - 买入/定投: 增加份额、更新成本价和累计投入、并尝试更新市值/盈亏
    - 卖出: 减少份额、减少累计投入(按比例)、并尝试更新市值/盈亏
    """
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    holding = get_holding(db, fund_code, platform)

    if tx_type in ("买入", "定投"):
        if holding:
            # 更新已有持仓
            old_shares = holding["holding_shares"] or 0
            old_cost = holding["avg_buy_price"] or 0
            old_invested = holding["invested_capital"] or 0

            new_shares = round(old_shares + shares, 2)
            # 加权平均成本价
            if new_shares > 0:
                new_cost = round(
                    (old_shares * old_cost + shares * (nav_at_tx or 0))
                    / new_shares, 4
                )
            else:
                new_cost = nav_at_tx or old_cost

            new_invested = round(old_invested + (amount or 0), 2)
            new_base = round(new_shares * 0.2, 2)
            
            # 尝试根据交易净值更新市值和盈亏
            # 如果没有提供 nav_at_tx，则沿用旧的 current_price (如果存在)
            current_price = holding["current_price"]
            if nav_at_tx and nav_at_tx > 0:
                current_price = nav_at_tx
            
            # 如果依然没有 current_price，则无法准确计算市值，暂且用成本价估算或保持为0
            calc_price = current_price if (current_price and current_price > 0) else new_cost
            
            holding_value = round(new_shares * calc_price, 2)
            profit_loss = round(holding_value - new_invested, 2)
            return_rate = round(profit_loss / new_invested * 100, 2) if new_invested > 0 else 0
            
            # 更新持仓
            db.execute(
                "UPDATE fund_holdings SET holding_shares=?, avg_buy_price=?, "
                "base_shares=?, invested_capital=?, "
                "current_price=?, holding_value=?, profit_loss_amount=?, return_rate=?, "
                "updated_at=? WHERE fund_code=? AND platform=?",
                (new_shares, new_cost, new_base,
                 new_invested, 
                 current_price, holding_value, profit_loss, return_rate,
                 today, fund_code, platform),
            )
        else:
            # 新建持仓
            # 从 fund_info 获取基金名称
            fi = db.execute(
                "SELECT fund_name FROM fund_info WHERE fund_code=?",
                (fund_code,),
            ).fetchone()
            fund_name = fi["fund_name"] if fi else fund_code

            cost = nav_at_tx or (amount / shares if shares > 0 else 0)
            base = round(shares * 0.2, 2)
            
            current_price = nav_at_tx or cost
            invested = round(amount or 0, 2)
            holding_value = round(shares * current_price, 2)
            profit_loss = round(holding_value - invested, 2)
            return_rate = round(profit_loss / invested * 100, 2) if invested > 0 else 0
            
            db.execute(
                "INSERT INTO fund_holdings "
                "(fund_code, fund_name, platform, holding_shares, avg_buy_price, "
                "base_shares, invested_capital, "
                "current_price, holding_value, profit_loss_amount, return_rate, "
                "first_buy_date, updated_at, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (fund_code, fund_name, platform, round(shares, 2),
                 round(cost, 4), base,
                 invested,
                 current_price, holding_value, profit_loss, return_rate,
                 today, today, today),
            )

    elif tx_type == "卖出":
        if not holding:
            return  # 无持仓可卖，静默跳过
        old_shares = holding["holding_shares"] or 0
        old_invested = holding["invested_capital"] or 0

        new_shares = round(old_shares - shares, 2)
        if new_shares < 0:
            new_shares = 0

        # 按卖出份额占比减少累计投入
        if old_shares > 0:
            sell_ratio = shares / old_shares
            new_invested = round(old_invested * (1 - sell_ratio), 2)
        else:
            new_invested = 0

        new_base = round(new_shares * 0.2, 2)
        
        # 更新市值
        current_price = holding["current_price"]
        if nav_at_tx and nav_at_tx > 0:
            current_price = nav_at_tx
            
        calc_price = current_price if (current_price and current_price > 0) else (holding["avg_buy_price"] or 0)
        
        holding_value = round(new_shares * calc_price, 2)
        profit_loss = round(holding_value - new_invested, 2)
        return_rate = round(profit_loss / new_invested * 100, 2) if new_invested > 0 else 0

        db.execute(
            "UPDATE fund_holdings SET holding_shares=?, base_shares=?, "
            "invested_capital=?, "
            "current_price=?, holding_value=?, profit_loss_amount=?, return_rate=?, "
            "updated_at=? "
            "WHERE fund_code=? AND platform=?",
            (new_shares, new_base, new_invested,
             current_price, holding_value, profit_loss, return_rate,
             today, fund_code, platform),
        )

    # 其他类型(分红/转换等)暂不处理
