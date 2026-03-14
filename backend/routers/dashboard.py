from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import FundHolding, FundInfo, TradeRecord, DailyQuote
from ..schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _latest_quotes_subquery(db: Session):
    """构建获取每个基金最新净值的子查询（与 holdings.py 一致）"""
    subq = db.query(
        DailyQuote.fund_code,
        func.max(DailyQuote.quote_date).label('max_date')
    ).group_by(DailyQuote.fund_code).subquery()

    return db.query(DailyQuote).join(
        subq,
        (DailyQuote.fund_code == subq.c.fund_code) &
        (DailyQuote.quote_date == subq.c.max_date)
    ).subquery()


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)):
    """获取仪表盘汇总数据（使用最新净值实时计算）"""
    latest_quotes = _latest_quotes_subquery(db)

    # 查询所有持仓，JOIN 最新净值
    rows = db.query(
        FundHolding,
        FundInfo,
        latest_quotes.c.close_price.label('latest_nav'),
    ).outerjoin(FundInfo, FundHolding.fund_code == FundInfo.fund_code) \
     .outerjoin(latest_quotes, FundHolding.fund_code == latest_quotes.c.fund_code) \
     .all()

    total_assets = 0.0
    total_invested = 0.0   # 累计买入总金额
    total_sold = 0.0       # 累计卖出总金额
    net_invested = 0.0     # 净投入
    total_pnl = 0.0
    fund_codes_with_shares = set()

    cat_map = {}   # category -> value
    plat_map = {}  # platform -> value

    for holding, fund_info, latest_nav in rows:
        shares = holding.holding_shares or 0
        cost_price = holding.avg_buy_price or 0
        h_invested = holding.invested_capital or 0
        h_sold = holding.total_sold or 0
        h_net = holding.net_invested or 0

        # 累计资金流
        total_invested += h_invested
        total_sold += h_sold
        net_invested += h_net

        # 使用最新净值计算市值（与 holdings.py 口径一致）
        if latest_nav and latest_nav > 0:
            current_value = round(shares * latest_nav, 2)
        elif holding.holding_value and holding.holding_value > 0:
            current_value = holding.holding_value
        else:
            current_value = round(shares * cost_price, 2)

        # 盈亏基于持有成本
        cost_value = round(shares * cost_price, 2)
        pnl = round(current_value - cost_value, 2)

        total_assets += current_value
        total_pnl += pnl

        if shares > 0:
            fund_codes_with_shares.add(holding.fund_code)

        # 分类分布
        category = (fund_info.fund_category if fund_info else None) or '其他'
        cat_map[category] = cat_map.get(category, 0) + current_value

        # 平台分布
        plat = holding.platform or '未知'
        plat_map[plat] = plat_map.get(plat, 0) + current_value

    # 收益率：基于持有成本
    total_cost = sum(
        round((h.holding_shares or 0) * (h.avg_buy_price or 0), 2)
        for h, _, _ in rows
    )
    pnl_rate = round(total_pnl / total_cost * 100, 2) if total_cost > 0 else 0

    # 分类分布（按市值降序）
    category_distribution = sorted(
        [{"category": k, "value": round(v, 2)} for k, v in cat_map.items()],
        key=lambda x: x["value"], reverse=True
    )

    # 平台分布（按市值降序）
    platform_distribution = sorted(
        [{"platform": k, "value": round(v, 2)} for k, v in plat_map.items()],
        key=lambda x: x["value"], reverse=True
    )

    # 待执行记录数
    pending_count = db.query(TradeRecord).filter(TradeRecord.exec_status == '待执行').count()

    return DashboardSummary(
        total_assets=round(total_assets, 2),
        total_invested=round(total_invested, 2),
        total_sold=round(total_sold, 2),
        net_invested=round(net_invested, 2),
        total_pnl=round(total_pnl, 2),
        pnl_rate=round(pnl_rate, 2),
        fund_count=len(fund_codes_with_shares),
        category_distribution=category_distribution,
        platform_distribution=platform_distribution,
        pending_records=pending_count,
    )
