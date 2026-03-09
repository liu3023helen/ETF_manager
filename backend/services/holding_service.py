"""
持仓 Service 层
封装 fund_holdings 的增删改查业务逻辑，供 Router 调用
"""
from sqlalchemy.orm import Session
from datetime import datetime
from ..models import FundHolding, FundInfo


def get_holding(db: Session, fund_code: str, platform: str):
    """根据基金代码+平台获取持仓记录"""
    return db.query(FundHolding).filter(
        FundHolding.fund_code == fund_code,
        FundHolding.platform == platform
    ).first()


def apply_transaction(db: Session, tx_type: str, fund_code: str,
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
        if not shares or shares <= 0:
            raise ValueError("买入/定投份额必须大于0")

        effective_nav = nav_at_tx if (nav_at_tx and nav_at_tx > 0) else ((amount / shares) if amount and amount > 0 else 0)

        if holding:
            # 更新已有持仓
            old_shares = holding.holding_shares or 0
            old_cost = holding.avg_buy_price or 0
            old_invested = holding.invested_capital or 0

            new_shares = round(old_shares + shares, 2)
            # 加权平均成本价（无 nav 时回退到旧成本）
            nav_for_cost = effective_nav if effective_nav > 0 else old_cost
            if new_shares > 0:
                new_cost = round((old_shares * old_cost + shares * nav_for_cost) / new_shares, 4)
            else:
                new_cost = nav_for_cost

            tx_amount = round(amount, 2) if (amount and amount > 0) else round(shares * nav_for_cost, 2)
            new_invested = round(old_invested + tx_amount, 2)
            new_base = round(new_shares * 0.2, 2)

            # 优先使用交易净值，否则沿用旧 current_price，再回退新成本
            current_price = holding.current_price
            if effective_nav > 0:
                current_price = effective_nav

            calc_price = current_price if (current_price and current_price > 0) else new_cost

            holding_value = round(new_shares * calc_price, 2)
            profit_loss = round(holding_value - new_invested, 2)
            return_rate = round(profit_loss / new_invested * 100, 2) if new_invested > 0 else 0

            # 更新持仓
            holding.holding_shares = new_shares
            holding.avg_buy_price = new_cost
            holding.base_shares = new_base
            holding.invested_capital = new_invested
            holding.current_price = current_price
            holding.holding_value = holding_value
            holding.profit_loss_amount = profit_loss
            holding.return_rate = return_rate
            holding.updated_at = today

        else:
            # 新建持仓
            cost = effective_nav if effective_nav > 0 else 0
            base = round(shares * 0.2, 2)

            current_price = cost
            invested = round(amount, 2) if (amount and amount > 0) else round(shares * cost, 2)
            holding_value = round(shares * current_price, 2)
            profit_loss = round(holding_value - invested, 2)
            return_rate = round(profit_loss / invested * 100, 2) if invested > 0 else 0

            new_holding = FundHolding(
                fund_code=fund_code,
                platform=platform,
                holding_shares=round(shares, 2),
                avg_buy_price=round(cost, 4),
                base_shares=base,
                invested_capital=invested,
                current_price=current_price,
                holding_value=holding_value,
                profit_loss_amount=profit_loss,
                return_rate=return_rate,
                first_buy_date=today,
                updated_at=today,
                created_at=today
            )
            db.add(new_holding)

    elif tx_type == "卖出":
        if not holding:
            return  # 无持仓可卖，静默跳过

        if not shares or shares <= 0:
            raise ValueError("卖出份额必须大于0")

        old_shares = holding.holding_shares or 0
        old_invested = holding.invested_capital or 0
        if old_shares <= 0:
            return

        # 卖出份额不得超过当前持仓
        sell_shares = min(shares, old_shares)
        new_shares = round(old_shares - sell_shares, 2)

        # 按卖出份额占比减少累计投入，且不允许负值
        sell_ratio = sell_shares / old_shares
        new_invested = max(0, round(old_invested * (1 - sell_ratio), 2))

        new_base = round(new_shares * 0.2, 2)

        # 更新市值
        current_price = holding.current_price
        if nav_at_tx and nav_at_tx > 0:
            current_price = nav_at_tx

        calc_price = current_price if (current_price and current_price > 0) else (holding.avg_buy_price or 0)

        holding_value = round(new_shares * calc_price, 2)
        profit_loss = round(holding_value - new_invested, 2)
        return_rate = round(profit_loss / new_invested * 100, 2) if new_invested > 0 else 0

        holding.holding_shares = new_shares
        holding.base_shares = new_base
        holding.invested_capital = new_invested
        holding.current_price = current_price
        holding.holding_value = holding_value
        holding.profit_loss_amount = profit_loss
        holding.return_rate = return_rate
        holding.updated_at = today

    # 其他类型(分红/转换等)暂不处理

