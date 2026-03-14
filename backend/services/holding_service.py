"""
持仓 Service 层
封装 fund_holdings 的增删改查业务逻辑，供 Router 调用
"""
from sqlalchemy.orm import Session
from datetime import datetime
from ..models import FundHolding, FundInfo, TradeRecord


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
    - 卖出: 减少份额、更新累计卖出/净投入、并尝试更新市值/盈亏
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
            old_total_sold = holding.total_sold or 0

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
            cost_value = round(new_shares * new_cost, 2)
            profit_loss = round(holding_value - cost_value, 2)
            return_rate = round(profit_loss / cost_value * 100, 2) if cost_value > 0 else 0

            # 更新持仓
            holding.holding_shares = new_shares
            holding.avg_buy_price = new_cost
            holding.base_shares = new_base
            holding.invested_capital = new_invested
            holding.total_sold = old_total_sold  # 买入不影响卖出累计
            holding.net_invested = round(new_invested - old_total_sold, 2)
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
            cost_value = round(shares * cost, 2)
            profit_loss = round(holding_value - cost_value, 2)
            return_rate = round(profit_loss / cost_value * 100, 2) if cost_value > 0 else 0

            new_holding = FundHolding(
                fund_code=fund_code,
                platform=platform,
                holding_shares=round(shares, 2),
                avg_buy_price=round(cost, 4),
                base_shares=base,
                invested_capital=invested,
                total_sold=0,
                net_invested=invested,
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
        if old_shares <= 0:
            return

        old_invested = holding.invested_capital or 0
        old_total_sold = holding.total_sold or 0

        # 卖出份额不得超过当前持仓
        sell_shares = min(shares, old_shares)
        new_shares = round(old_shares - sell_shares, 2)
        new_base = round(new_shares * 0.2, 2)

        # invested_capital 不变（累计买入总金额，卖出不扣减）
        # total_sold 增加卖出回收金额
        sell_nav = nav_at_tx if (nav_at_tx and nav_at_tx > 0) else (holding.avg_buy_price or 0)
        sell_amount = round(amount, 2) if (amount and amount > 0) else round(sell_shares * sell_nav, 2)
        new_total_sold = round(old_total_sold + sell_amount, 2)
        new_net_invested = round(old_invested - new_total_sold, 2)

        # 更新当前净值
        current_price = holding.current_price
        if nav_at_tx and nav_at_tx > 0:
            current_price = nav_at_tx

        calc_price = current_price if (current_price and current_price > 0) else (holding.avg_buy_price or 0)

        # 盈亏基于持有成本 = 份额 * 成本价
        cost_price = holding.avg_buy_price or 0
        holding_value = round(new_shares * calc_price, 2)
        cost_value = round(new_shares * cost_price, 2)
        profit_loss = round(holding_value - cost_value, 2)
        return_rate = round(profit_loss / cost_value * 100, 2) if cost_value > 0 else 0

        holding.holding_shares = new_shares
        holding.base_shares = new_base
        # holding.invested_capital 保持不变
        holding.total_sold = new_total_sold
        holding.net_invested = new_net_invested
        holding.current_price = current_price
        holding.holding_value = holding_value
        holding.profit_loss_amount = profit_loss
        holding.return_rate = return_rate
        holding.updated_at = today

    # 其他类型(分红/转换等)暂不处理


def rebuild_holding(db: Session, fund_code: str, platform: str) -> None:
    """
    根据 trade_records 全量回放，重建指定基金+平台的 fund_holdings 记录。
    清零后按 record_date ASC 逐笔累积：份额、成本价、invested_capital、total_sold、net_invested。
    
    如果该组合没有任何已执行交易，则将持仓清零但保留记录。
    """
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 获取该基金+平台的全部已执行交易，按时间排序
    trades = db.query(TradeRecord).filter(
        TradeRecord.fund_code == fund_code,
        TradeRecord.platform == platform,
        TradeRecord.exec_status == '已执行',
        TradeRecord.record_type.in_(['买入', '卖出', '定投'])
    ).order_by(TradeRecord.record_date.asc(), TradeRecord.record_id.asc()).all()

    # 从零开始回放
    holding_shares = 0.0
    avg_buy_price = 0.0
    invested_capital = 0.0
    total_sold = 0.0
    first_buy_date = None
    current_price = 0.0

    for trade in trades:
        t_type = trade.record_type
        t_amount = trade.amount or 0
        t_shares = trade.shares or 0
        t_nav = trade.nav or 0

        if t_type in ('买入', '定投'):
            if t_shares <= 0:
                continue

            effective_nav = t_nav if t_nav > 0 else (t_amount / t_shares if t_amount > 0 else 0)
            nav_for_cost = effective_nav if effective_nav > 0 else avg_buy_price

            old_shares = holding_shares
            old_cost = avg_buy_price
            new_shares = round(old_shares + t_shares, 2)

            if new_shares > 0:
                avg_buy_price = round(
                    (old_shares * old_cost + t_shares * nav_for_cost) / new_shares, 4
                )

            holding_shares = new_shares
            tx_amount = round(t_amount, 2) if t_amount > 0 else round(t_shares * nav_for_cost, 2)
            invested_capital = round(invested_capital + tx_amount, 2)

            if effective_nav > 0:
                current_price = effective_nav

            if first_buy_date is None:
                first_buy_date = trade.record_date

        elif t_type == '卖出':
            if t_shares <= 0 or holding_shares <= 0:
                continue

            sell_shares = min(t_shares, holding_shares)
            holding_shares = round(holding_shares - sell_shares, 2)

            sell_nav = t_nav if t_nav > 0 else avg_buy_price
            sell_amount = round(t_amount, 2) if t_amount > 0 else round(sell_shares * sell_nav, 2)
            total_sold = round(total_sold + sell_amount, 2)

            if t_nav and t_nav > 0:
                current_price = t_nav

    # 计算衍生字段
    net_invested = round(invested_capital - total_sold, 2)
    base_shares = round(holding_shares * 0.2, 2)

    calc_price = current_price if current_price > 0 else avg_buy_price
    holding_value = round(holding_shares * calc_price, 2)
    cost_value = round(holding_shares * avg_buy_price, 2)
    profit_loss = round(holding_value - cost_value, 2)
    return_rate = round(profit_loss / cost_value * 100, 2) if cost_value > 0 else 0

    # 更新或保留持仓记录
    holding = get_holding(db, fund_code, platform)
    if holding:
        holding.holding_shares = holding_shares
        holding.avg_buy_price = avg_buy_price
        holding.base_shares = base_shares
        holding.invested_capital = invested_capital
        holding.total_sold = total_sold
        holding.net_invested = net_invested
        holding.current_price = current_price if current_price > 0 else holding.current_price
        holding.holding_value = holding_value
        holding.profit_loss_amount = profit_loss
        holding.return_rate = return_rate
        holding.first_buy_date = first_buy_date or holding.first_buy_date
        holding.updated_at = today
    elif trades:
        # 有交易但无持仓记录（理论上不应发生），创建一条
        new_holding = FundHolding(
            fund_code=fund_code,
            platform=platform,
            holding_shares=holding_shares,
            avg_buy_price=avg_buy_price,
            base_shares=base_shares,
            invested_capital=invested_capital,
            total_sold=total_sold,
            net_invested=net_invested,
            current_price=current_price,
            holding_value=holding_value,
            profit_loss_amount=profit_loss,
            return_rate=return_rate,
            first_buy_date=first_buy_date,
            updated_at=today,
            created_at=today,
        )
        db.add(new_holding)
