from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import FundInfo
from ..schemas import FundInfo as FundInfoSchema

router = APIRouter(prefix="/api/funds", tags=["funds"])


@router.get("", response_model=List[FundInfoSchema])
def list_funds(category: str = None, db: Session = Depends(get_db)):
    query = db.query(FundInfo)
    if category:
        query = query.filter(FundInfo.fund_category == category)
    query = query.order_by(FundInfo.fund_code)
    return query.all()


@router.get("/{fund_code}", response_model=FundInfoSchema)
def get_fund(fund_code: str, db: Session = Depends(get_db)):
    fund = db.query(FundInfo).filter(FundInfo.fund_code == fund_code).first()
    if not fund:
        raise HTTPException(status_code=404, detail="基金不存在")
    return fund
