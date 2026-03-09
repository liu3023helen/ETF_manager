from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import FundHolding, FundInfo, TradeRecord
from ..schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)):
    # 总资产、总投入、总盈亏
    total_assets = db.query(func.coalesce(func.sum(FundHolding.holding_value), 0)).scalar() or 0
    total_invested = db.query(func.coalesce(func.sum(FundHolding.invested_capital), 0)).scalar() or 0
    total_pnl = db.query(func.coalesce(func.sum(FundHolding.profit_loss_amount), 0)).scalar() or 0
    
    pnl_rate = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    # 持仓基金数
    fund_count = db.query(func.count(func.distinct(FundHolding.fund_code))).filter(FundHolding.holding_shares > 0).scalar() or 0

    # 按分类分布 (市值)
    cat_rows = db.query(
        func.coalesce(FundInfo.fund_category, '其他').label('category'),
        func.sum(FundHolding.holding_value).label('value')
    ).outerjoin(FundInfo, FundHolding.fund_code == FundInfo.fund_code).group_by(
        func.coalesce(FundInfo.fund_category, '其他')
    ).order_by(func.sum(FundHolding.holding_value).desc()).all()
    
    category_distribution = [
        {"category": r.category, "value": round(r.value or 0, 2)}
        for r in cat_rows
    ]

    # 按平台分布 (市值)
    plat_rows = db.query(
        FundHolding.platform,
        func.sum(FundHolding.holding_value).label('value')
    ).group_by(FundHolding.platform).order_by(func.sum(FundHolding.holding_value).desc()).all()
    
    platform_distribution = [
        {"platform": r.platform, "value": round(r.value or 0, 2)}
        for r in plat_rows
    ]

    # 待执行记录数
    pending_count = db.query(TradeRecord).filter(TradeRecord.exec_status == '待执行').count()

    return DashboardSummary(
        total_assets=round(total_assets, 2),
        total_invested=round(total_invested, 2),
        total_pnl=round(total_pnl, 2),
        pnl_rate=round(pnl_rate, 2),
        fund_count=fund_count,
        category_distribution=category_distribution,
        platform_distribution=platform_distribution,
        pending_records=pending_count,
    )
