from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from ..database import get_db

router = APIRouter(prefix="/api/funds", tags=["funds"])


@router.get("")
def list_funds(category: str = None, db: sqlite3.Connection = Depends(get_db)):
    if category:
        rows = db.execute(
            "SELECT * FROM fund_info WHERE fund_category=? ORDER BY fund_code",
            (category,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM fund_info ORDER BY fund_code"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{fund_code}")
def get_fund(fund_code: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT * FROM fund_info WHERE fund_code=?", (fund_code,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="基金不存在")
    return dict(row)
