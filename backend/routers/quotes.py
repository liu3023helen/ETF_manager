from fastapi import APIRouter, Depends
import sqlite3
from ..database import get_db

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.get("")
def list_quotes(
    fund_code: str = None,
    date_from: str = None,
    date_to: str = None,
    db: sqlite3.Connection = Depends(get_db),
):
    sql = (
        "SELECT q.*, f.fund_name FROM daily_quotes q "
        "LEFT JOIN fund_info f ON q.fund_code=f.fund_code WHERE 1=1"
    )
    params = []
    if fund_code:
        sql += " AND q.fund_code=?"
        params.append(fund_code)
    if date_from:
        sql += " AND q.date>=?"
        params.append(date_from)
    if date_to:
        sql += " AND q.date<=?"
        params.append(date_to)
    sql += " ORDER BY q.date DESC, q.fund_code"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
