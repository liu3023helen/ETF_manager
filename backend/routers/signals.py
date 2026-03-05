from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from ..database import get_db
from ..models import SignalStatusUpdate

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("")
def list_signals(status: str = None, db: sqlite3.Connection = Depends(get_db)):
    sql = (
        "SELECT s.*, f.fund_name FROM trade_signals s "
        "LEFT JOIN fund_info f ON s.fund_code=f.fund_code WHERE 1=1"
    )
    params = []
    if status:
        sql += " AND s.exec_status=?"
        params.append(status)
    sql += " ORDER BY s.signal_date DESC, s.signal_id DESC"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.patch("/{signal_id}")
def update_signal_status(
    signal_id: int,
    update: SignalStatusUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute(
        "SELECT signal_id FROM trade_signals WHERE signal_id=?", (signal_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"信号 {signal_id} 不存在")
    db.execute(
        "UPDATE trade_signals SET exec_status=?, actual_action=? WHERE signal_id=?",
        (update.exec_status, update.actual_action, signal_id),
    )
    db.commit()
    return {"message": "信号状态已更新"}
