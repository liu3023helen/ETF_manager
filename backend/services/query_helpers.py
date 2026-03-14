"""
公共查询工具函数
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import DailyQuote


def latest_quotes_subquery(db: Session):
    """构建获取每个基金最新净值的子查询

    返回一个子查询，包含字段：fund_code, quote_date, close_price 等。
    dashboard.py 和 holdings.py 均使用此函数来获取最新净值。
    """
    subq = db.query(
        DailyQuote.fund_code,
        func.max(DailyQuote.quote_date).label('max_date')
    ).group_by(DailyQuote.fund_code).subquery()

    return db.query(DailyQuote).join(
        subq,
        (DailyQuote.fund_code == subq.c.fund_code) &
        (DailyQuote.quote_date == subq.c.max_date)
    ).subquery()
