from fastapi import APIRouter, Depends
import sqlite3
from ..database import get_db
from ..models import TransactionCreate

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    fund_code: str = None,
    platform: str = None,
    tx_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: sqlite3.Connection = Depends(get_db),
):
    sql = (
        "SELECT t.*, f.fund_name FROM transactions t "
        "LEFT JOIN fund_info f ON t.fund_code=f.fund_code WHERE 1=1"
    )
    params = []
    if fund_code:
        sql += " AND t.fund_code=?"
        params.append(fund_code)
    if platform:
        sql += " AND t.platform=?"
        params.append(platform)
    if tx_type:
        sql += " AND t.tx_type=?"
        params.append(tx_type)
    if date_from:
        sql += " AND t.tx_date>=?"
        params.append(date_from)
    if date_to:
        sql += " AND t.tx_date<=?"
        params.append(date_to)
    sql += " ORDER BY t.tx_date DESC, t.tx_id DESC"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.post("")
def create_transaction(
    tx: TransactionCreate, db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.execute(
        "INSERT INTO transactions (fund_code, platform, tx_type, tx_date, amount, shares, nav_at_tx, fee, note) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            tx.fund_code,
            tx.platform,
            tx.tx_type,
            tx.tx_date,
            tx.amount,
            tx.shares,
            tx.nav_at_tx,
            tx.fee,
            tx.note,
        ),
    )
    db.commit()
    return {"tx_id": cursor.lastrowid, "message": "交易记录创建成功"}
