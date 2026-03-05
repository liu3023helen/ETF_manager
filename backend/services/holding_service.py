"""
持仓 Service 层
封装 my_holdings 的增删改查业务逻辑，供 Router 调用
"""
import sqlite3
from datetime import datetime


def get_holding(db: sqlite3.Connection, fund_code: str, platform: str):
    """根据基金代码+平台获取持仓记录"""
    row = db.execute(
        "SELECT * FROM my_holdings WHERE fund_code=? AND platform=?",
        (fund_code, platform),
    ).fetchone()
    return dict(row) if row else None


def apply_transaction(db: sqlite3.Connection, tx_type: str, fund_code: str,
                      platform: str, amount: float, shares: float,
                      nav_at_tx: float = None):
    """
    根据交易类型更新 my_holdings
    - 买入/定投: 增加份额、更新成本价和累计投入
    - 卖出: 减少份额、减少累计投入(按比例)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    holding = get_holding(db, fund_code, platform)

    if tx_type in ("买入", "定投"):
        if holding:
            # 更新已有持仓
            old_shares = holding["shares"] or 0
            old_cost = holding["cost_price"] or 0
            old_invested = holding["total_invested"] or 0

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
            new_tradable = round(new_shares - new_base, 2)

            db.execute(
                "UPDATE my_holdings SET shares=?, cost_price=?, "
                "base_shares=?, tradable_shares=?, total_invested=?, "
                "updated_at=? WHERE fund_code=? AND platform=?",
                (new_shares, new_cost, new_base, new_tradable,
                 new_invested, today, fund_code, platform),
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
            tradable = round(shares - base, 2)

            db.execute(
                "INSERT INTO my_holdings "
                "(fund_code, fund_name, platform, shares, cost_price, "
                "base_shares, tradable_shares, total_invested, "
                "first_buy_date, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (fund_code, fund_name, platform, round(shares, 2),
                 round(cost, 4), base, tradable,
                 round(amount or 0, 2), today, today),
            )

    elif tx_type == "卖出":
        if not holding:
            return  # 无持仓可卖，静默跳过
        old_shares = holding["shares"] or 0
        old_invested = holding["total_invested"] or 0

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
        new_tradable = round(new_shares - new_base, 2)

        db.execute(
            "UPDATE my_holdings SET shares=?, base_shares=?, "
            "tradable_shares=?, total_invested=?, updated_at=? "
            "WHERE fund_code=? AND platform=?",
            (new_shares, new_base, new_tradable, new_invested,
             today, fund_code, platform),
        )

    # 其他类型(分红/转换等)暂不处理
