from fastapi import APIRouter, Depends, Query
import sqlite3
from ..database import get_db

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.get("")
def list_quotes(
    fund_code: str = None,
    date_from: str = None,
    date_to: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: sqlite3.Connection = Depends(get_db),
):
    where = " WHERE 1=1"
    params = []
    if fund_code:
        where += " AND q.fund_code=?"
        params.append(fund_code)
    if date_from:
        where += " AND q.quote_date>=?"
        params.append(date_from)
    if date_to:
        where += " AND q.quote_date<=?"
        params.append(date_to)

    # 总记录数
    count_sql = (
        "SELECT COUNT(*) FROM daily_quotes q" + where
    )
    total = db.execute(count_sql, params).fetchone()[0]

    # 分页查询
    sql = (
        "SELECT q.* FROM daily_quotes q "
        + where
        + " ORDER BY q.quote_date DESC, q.fund_code"
        + " LIMIT ? OFFSET ?"
    )
    offset = (page - 1) * page_size
    rows = db.execute(sql, params + [page_size, offset]).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [dict(r) for r in rows],
    }
