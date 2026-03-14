from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import FundHolding, FundInfo
from ..schemas import HoldingDetail
from ..services.query_helpers import latest_quotes_subquery

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


def _build_holding_item(holding: FundHolding, fund_info: FundInfo,
                        latest_nav: float, nav_date: str) -> dict:
    """将 ORM 结果组装为前端需要的持仓字典"""
    shares = holding.holding_shares or 0
    base_shares = holding.base_shares or 0
    total_invested = holding.invested_capital or 0
    total_sold = holding.total_sold or 0
    net_invested = holding.net_invested or 0

    item = {
        "holding_id": holding.holding_id,
        "fund_code": holding.fund_code,
        "fund_name": fund_info.fund_name if fund_info else None,
        "fund_category": fund_info.fund_category if fund_info else None,
        "platform": holding.platform,
        "shares": shares,
        "cost_price": holding.avg_buy_price or 0,
        "base_shares": base_shares,
        "tradable_shares": round(shares - base_shares, 2),
        "total_invested": total_invested,
        "total_sold": total_sold,
        "net_invested": net_invested,
        "first_buy_date": holding.first_buy_date,
        "updated_at": holding.updated_at,
        "risk_level": fund_info.risk_level if fund_info else None,
        "latest_nav": latest_nav,
        "nav_date": nav_date,
        "dca_is_active": holding.dca_is_active,
        "dca_frequency": holding.dca_frequency,
        "dca_amount": holding.dca_amount,
        "dca_type": holding.dca_type,
        "dca_total_invested": holding.dca_total_invested,
    }

    # 计算市值与盈亏，优先级：最新净值 > DB 存值 > 成本价估算
    # 盈亏基于持有成本 = 份额 × 成本价
    cost_price = holding.avg_buy_price or 0
    cost_value = round(shares * cost_price, 2)

    if latest_nav and latest_nav > 0:
        current_value = round(shares * latest_nav, 2)
        item["holding_value"] = current_value
        item["current_price"] = latest_nav
        item["profit_loss_amount"] = round(current_value - cost_value, 2)
        item["return_rate"] = round((current_value - cost_value) / cost_value * 100, 2) if cost_value > 0 else 0
    elif holding.holding_value and holding.holding_value > 0:
        current_value = holding.holding_value
        item["holding_value"] = current_value
        item["current_price"] = holding.current_price
        item["profit_loss_amount"] = round(current_value - cost_value, 2)
        item["return_rate"] = round((current_value - cost_value) / cost_value * 100, 2) if cost_value > 0 else 0
    else:
        current_value = cost_value
        item["holding_value"] = current_value
        item["current_price"] = holding.current_price
        item["profit_loss_amount"] = 0
        item["return_rate"] = 0

    item["current_value"] = current_value
    return item


@router.get("", response_model=List[HoldingDetail])
def list_holdings(platform: str = None, db: Session = Depends(get_db)):
    latest_quotes = latest_quotes_subquery(db)

    query = db.query(
        FundHolding,
        FundInfo,
        latest_quotes.c.close_price.label('latest_nav'),
        latest_quotes.c.quote_date.label('nav_date')
    ).outerjoin(FundInfo, FundHolding.fund_code == FundInfo.fund_code) \
     .outerjoin(latest_quotes, FundHolding.fund_code == latest_quotes.c.fund_code)

    if platform:
        query = query.filter(FundHolding.platform == platform)

    query = query.order_by(FundHolding.holding_id)
    rows = query.all()

    return [_build_holding_item(h, fi, nav, nd) for h, fi, nav, nd in rows]


@router.get("/{holding_id}", response_model=HoldingDetail)
def get_holding(holding_id: int, db: Session = Depends(get_db)):
    latest_quotes = _latest_quotes_subquery(db)

    result = db.query(
        FundHolding,
        FundInfo,
        latest_quotes.c.close_price.label('latest_nav'),
        latest_quotes.c.quote_date.label('nav_date')
    ).outerjoin(FundInfo, FundHolding.fund_code == FundInfo.fund_code) \
     .outerjoin(latest_quotes, FundHolding.fund_code == latest_quotes.c.fund_code) \
     .filter(FundHolding.holding_id == holding_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="持仓记录不存在")

    holding, fund_info, latest_nav, nav_date = result
    return _build_holding_item(holding, fund_info, latest_nav, nav_date)


@router.delete("/{holding_id}")
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    holding = db.query(FundHolding).filter(FundHolding.holding_id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="持仓记录不存在")

    db.delete(holding)
    db.commit()
    return {"message": "持仓记录已删除"}
