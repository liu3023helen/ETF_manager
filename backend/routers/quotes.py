from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DailyQuote, FundInfo

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.get("")
def list_quotes(
    fund_code: str = None,
    date_from: str = None,
    date_to: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(DailyQuote, FundInfo).outerjoin(
        FundInfo, DailyQuote.fund_code == FundInfo.fund_code
    )
    
    if fund_code:
        query = query.filter(DailyQuote.fund_code == fund_code)
    if date_from:
        query = query.filter(DailyQuote.quote_date >= date_from)
    if date_to:
        query = query.filter(DailyQuote.quote_date <= date_to)

    total = query.count()

    query = query.order_by(DailyQuote.quote_date.desc(), DailyQuote.fund_code)
    
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)
    
    rows = query.all()
    
    data = []
    for quote, fund_info in rows:
        item = {
            "id": quote.quote_id,
            "fund_code": quote.fund_code,
            "fund_name": fund_info.fund_name if fund_info else None,
            "date": quote.quote_date,
            "nav": quote.close_price,
            "acc_nav": quote.acc_nav,
        }
        data.append(item)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": data,
    }
