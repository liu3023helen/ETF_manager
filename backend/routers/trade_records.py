from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import sqlite3
from ..database import get_db
from ..models import TradeRecordCreate
from ..services.holding_service import apply_transaction

router = APIRouter(prefix="/api/trade-records", tags=["trade_records"])


@router.get("")
def list_records(
    fund_code: Optional[str] = None,
    record_type: Optional[str] = None,
    signal_type: Optional[str] = None,
    exec_status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: sqlite3.Connection = Depends(get_db),
):
    """列出交易记录（支持筛选和分页）"""
    base_sql = "FROM trade_records WHERE 1=1"
    params = []

    if fund_code:
        base_sql += " AND fund_code=?"
        params.append(fund_code)
    if record_type:
        base_sql += " AND record_type=?"
        params.append(record_type)
    if signal_type:
        base_sql += " AND signal_type=?"
        params.append(signal_type)
    if exec_status:
        base_sql += " AND exec_status=?"
        params.append(exec_status)
    if date_from:
        base_sql += " AND record_date>=?"
        params.append(date_from)
    if date_to:
        base_sql += " AND record_date<=?"
        params.append(date_to)

    # 总数
    total = db.execute(f"SELECT COUNT(*) as cnt {base_sql}", params).fetchone()["cnt"]

    # 分页查询
    offset = (page - 1) * page_size
    rows = db.execute(
        f"SELECT * {base_sql} ORDER BY record_date DESC, record_id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [dict(r) for r in rows],
    }


@router.get("/{record_id}")
def get_record(record_id: int, db: sqlite3.Connection = Depends(get_db)):
    """获取单条交易记录"""
    row = db.execute(
        "SELECT * FROM trade_records WHERE record_id=?", (record_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return dict(row)


@router.post("")
def create_record(
    record: TradeRecordCreate,
    db: sqlite3.Connection = Depends(get_db),
):
    """创建交易记录，并根据记录类型联动更新持仓"""
    try:
        cursor = db.execute(
            "INSERT INTO trade_records "
            "(fund_code, fund_name, record_type, record_date, platform, "
            "signal_type, trigger_condition, trigger_value, suggested_action, "
            "exec_status, exec_date, actual_action, "
            "amount, shares, nav, fee, note, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
            (
                record.fund_code,
                record.fund_name,
                record.record_type,
                record.record_date,
                record.platform,
                record.signal_type,
                record.trigger_condition,
                record.trigger_value,
                record.suggested_action,
                record.exec_status,
                record.exec_date,
                record.actual_action,
                record.amount,
                record.shares,
                record.nav,
                record.fee,
                record.note,
            ),
        )

        # 如果是实际交易类型（买入/卖出/定投），联动更新 fund_holdings
        if record.record_type in ("买入", "卖出", "定投") and record.shares and record.shares > 0:
            # 优先使用请求中的 platform，否则从现有持仓查
            platform = record.platform
            if not platform:
                holding = db.execute(
                    "SELECT platform FROM fund_holdings WHERE fund_code=? LIMIT 1",
                    (record.fund_code,),
                ).fetchone()
                platform = holding["platform"] if holding else "未知"

            apply_transaction(
                db, record.record_type, record.fund_code, platform,
                record.amount or 0, record.shares, record.nav,
            )

        db.commit()
        return {"record_id": cursor.lastrowid, "message": "记录创建成功"}
    except Exception as e:
        db.execute("ROLLBACK")
        raise HTTPException(status_code=500, detail=f"记录创建失败: {str(e)}")


@router.patch("/{record_id}")
def update_record(
    record_id: int,
    payload: dict,
    db: sqlite3.Connection = Depends(get_db),
):
    """更新交易记录（部分字段）"""
    row = db.execute(
        "SELECT * FROM trade_records WHERE record_id=?", (record_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 允许更新的字段白名单
    allowed_fields = {
        "exec_status", "exec_date", "actual_action",
        "amount", "shares", "nav", "fee", "note",
    }

    updates = []
    values = []
    for key, val in payload.items():
        if key in allowed_fields:
            updates.append(f"[{key}]=?")
            values.append(val)

    if not updates:
        raise HTTPException(status_code=400, detail="没有可更新的字段")

    values.append(record_id)
    db.execute(
        f"UPDATE trade_records SET {', '.join(updates)} WHERE record_id=?",
        values,
    )
    db.commit()
    return {"message": "记录已更新"}


@router.delete("/{record_id}")
def delete_record(record_id: int, db: sqlite3.Connection = Depends(get_db)):
    """删除交易记录"""
    row = db.execute(
        "SELECT record_id FROM trade_records WHERE record_id=?", (record_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.execute("DELETE FROM trade_records WHERE record_id=?", (record_id,))
    db.commit()
    return {"message": "记录已删除"}
