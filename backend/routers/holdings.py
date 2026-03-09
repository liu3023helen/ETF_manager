from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from ..database import get_db
from ..models import FundHolding, FundInfo, DailyQuote
from ..schemas import HoldingDetail

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


def reindex_holdings(db: Session):
    """重排 holding_id，保持从1开始连续不断"""
    holdings = db.query(FundHolding).order_by(FundHolding.fund_code, FundHolding.platform).all()
    for new_id, holding in enumerate(holdings, start=1):
        if holding.holding_id != new_id:
            holding.holding_id = -new_id
            
    db.commit()
    
    # 负数转正（避免两阶段冲突）
    holdings = db.query(FundHolding).filter(FundHolding.holding_id < 0).all()
    for holding in holdings:
        holding.holding_id = -holding.holding_id
        
    db.commit()


@router.get("", response_model=List[HoldingDetail])
def list_holdings(platform: str = None, db: Session = Depends(get_db)):
    # 子查询获取每个基金的最新净值日期
    subq = db.query(
        DailyQuote.fund_code,
        func.max(DailyQuote.quote_date).label('max_date')
    ).group_by(DailyQuote.fund_code).subquery()

    # 关联获取最新净值
    latest_quotes = db.query(DailyQuote).join(
        subq,
        (DailyQuote.fund_code == subq.c.fund_code) & 
        (DailyQuote.quote_date == subq.c.max_date)
    ).subquery()

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

    results = []
    for holding, fund_info, latest_nav, nav_date in rows:
        item = {
            "holding_id": holding.holding_id,
            "fund_code": holding.fund_code,
            "fund_name": fund_info.fund_name if fund_info else None,
            "fund_category": fund_info.fund_category if fund_info else None,
            "platform": holding.platform,
            "shares": holding.holding_shares or 0,
            "cost_price": holding.avg_buy_price or 0,
            "base_shares": holding.base_shares or 0,
            "total_invested": holding.invested_capital or 0,
            "first_buy_date": holding.first_buy_date,
            "updated_at": holding.updated_at,
            "dca_is_active": holding.dca_is_active,
            "dca_frequency": holding.dca_frequency,
            "dca_amount": holding.dca_amount,
            "dca_type": holding.dca_type,
            "dca_total_invested": holding.dca_total_invested,
            "risk_level": fund_info.risk_level if fund_info else None,
            "latest_nav": latest_nav,
            "nav_date": nav_date
        }
        
        # 计算可用份额
        shares = item["shares"]
        base_shares = item["base_shares"]
        item["tradable_shares"] = round(shares - base_shares, 2)
        total_invested = item["total_invested"]

        current_value = 0
        if latest_nav and latest_nav > 0:
            current_value = round(shares * latest_nav, 2)
            item["holding_value"] = current_value
            item["current_price"] = latest_nav
            item["profit_loss_amount"] = round(current_value - total_invested, 2)
            if total_invested > 0:
                item["return_rate"] = round((current_value - total_invested) / total_invested * 100, 2)
            else:
                item["return_rate"] = 0
        elif holding.holding_value and holding.holding_value > 0:
            current_value = holding.holding_value
            item["holding_value"] = holding.holding_value
            item["current_price"] = holding.current_price
            item["profit_loss_amount"] = holding.profit_loss_amount
            item["return_rate"] = holding.return_rate
        else:
            current_value = round(shares * item["cost_price"], 2)
            item["holding_value"] = current_value
            item["current_price"] = holding.current_price
            item["profit_loss_amount"] = holding.profit_loss_amount
            item["return_rate"] = holding.return_rate
        
        item["current_value"] = current_value
        results.append(item)
        
    return results


@router.get("/{holding_id}", response_model=HoldingDetail)
def get_holding(holding_id: int, db: Session = Depends(get_db)):
    result = db.query(FundHolding, FundInfo).outerjoin(
        FundInfo, FundHolding.fund_code == FundInfo.fund_code
    ).filter(FundHolding.holding_id == holding_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="持仓记录不存在")
        
    holding, fund_info = result
    
    item = {
        "holding_id": holding.holding_id,
        "fund_code": holding.fund_code,
        "fund_name": fund_info.fund_name if fund_info else None,
        "fund_category": fund_info.fund_category if fund_info else None,
        "platform": holding.platform,
        "shares": holding.holding_shares or 0,
        "cost_price": holding.avg_buy_price or 0,
        "base_shares": holding.base_shares or 0,
        "total_invested": holding.invested_capital or 0,
        "first_buy_date": holding.first_buy_date,
        "updated_at": holding.updated_at,
        "risk_level": fund_info.risk_level if fund_info else None,
        "holding_value": holding.holding_value,
        "profit_loss_amount": holding.profit_loss_amount,
        "return_rate": holding.return_rate,
        "current_price": holding.current_price
    }
    
    shares = item["shares"]
    base_shares = item["base_shares"]
    item["tradable_shares"] = round(shares - base_shares, 2)
    item["current_value"] = holding.holding_value or 0
    
    return item


@router.delete("/{holding_id}")
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    holding = db.query(FundHolding).filter(FundHolding.holding_id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="持仓记录不存在")
        
    db.delete(holding)
    db.commit()
    reindex_holdings(db)
    return {"message": "持仓记录已删除"}
