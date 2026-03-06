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
        platform = record.platform

        # 实际交易类型的业务校验
        if record.record_type in ("买入", "卖出", "定投"):
            if record.shares is None or record.shares <= 0:
                raise HTTPException(status_code=400, detail="买入/卖出/定投记录的 shares 必须大于0")

            # 买入/定投至少提供 amount 或 nav（二者都为空会导致投入金额不可计算）
            if record.record_type in ("买入", "定投") and not ((record.amount is not None and record.amount > 0) or (record.nav is not None and record.nav > 0)):
                raise HTTPException(status_code=400, detail="买入/定投记录必须提供 amount 或 nav")

            # 平台判定：优先请求值，否则尝试从持仓推断
            if not platform:
                rows = db.execute(
                    "SELECT DISTINCT platform FROM fund_holdings WHERE fund_code=?",
                    (record.fund_code,),
                ).fetchall()
                if len(rows) == 1:
                    platform = rows[0]["platform"]
                elif len(rows) > 1:
                    raise HTTPException(status_code=400, detail="该基金存在多个平台持仓，请指定 platform")
                else:
                    raise HTTPException(status_code=400, detail="新交易记录必须指定 platform")

            # 卖出时校验可卖份额
            if record.record_type == "卖出":
                holding = db.execute(
                    "SELECT holding_shares FROM fund_holdings WHERE fund_code=? AND platform=? LIMIT 1",
                    (record.fund_code, platform),
                ).fetchone()
                if not holding or (holding["holding_shares"] or 0) <= 0:
                    raise HTTPException(status_code=400, detail="当前平台无可卖持仓")
                if record.shares > (holding["holding_shares"] or 0):
                    raise HTTPException(status_code=400, detail="卖出份额不能超过当前持仓份额")

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
                platform,
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
        if record.record_type in ("买入", "卖出", "定投"):
            apply_transaction(
                db,
                record.record_type,
                record.fund_code,
                platform,
                record.amount or 0,
                record.shares,
                record.nav,
            )

        db.commit()
        return {"record_id": cursor.lastrowid, "message": "记录创建成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
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
