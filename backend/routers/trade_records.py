from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from ..database import get_db
from ..models import TradeRecord, FundHolding, FundInfo
from ..schemas import TradeRecordCreate
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
    db: Session = Depends(get_db),
):
    """列出交易记录（支持筛选和分页）"""
    query = db.query(TradeRecord, FundInfo).outerjoin(FundInfo, TradeRecord.fund_code == FundInfo.fund_code)

    if fund_code:
        query = query.filter(TradeRecord.fund_code == fund_code)
    if record_type:
        query = query.filter(TradeRecord.record_type == record_type)
    if signal_type:
        query = query.filter(TradeRecord.signal_type == signal_type)
    if exec_status:
        query = query.filter(TradeRecord.exec_status == exec_status)
    if date_from:
        query = query.filter(TradeRecord.record_date >= date_from)
    if date_to:
        query = query.filter(TradeRecord.record_date <= date_to)

    # 总数
    total = query.count()

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(TradeRecord.record_date.desc(), TradeRecord.record_id.desc())
    rows = query.offset(offset).limit(page_size).all()
    
    data = []
    for record, fund_info in rows:
        item = {
            "record_id": record.record_id,
            "fund_code": record.fund_code,
            "fund_name": fund_info.fund_name if fund_info else None,
            "record_type": record.record_type,
            "record_date": record.record_date,
            "signal_type": record.signal_type,
            "trigger_condition": record.trigger_condition,
            "trigger_value": record.trigger_value,
            "suggested_action": record.suggested_action,
            "exec_status": record.exec_status,
            "exec_date": record.exec_date,
            "actual_action": record.actual_action,
            "platform": record.platform,
            "amount": record.amount,
            "shares": record.shares,
            "nav": record.nav,
            "fee": record.fee,
            "note": record.note,
            "created_at": record.created_at,
        }
        data.append(item)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": data,
    }


@router.get("/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    """获取单条交易记录"""
    result = db.query(TradeRecord, FundInfo).outerjoin(
        FundInfo, TradeRecord.fund_code == FundInfo.fund_code
    ).filter(TradeRecord.record_id == record_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="记录不存在")
        
    record, fund_info = result
    
    return {
        "record_id": record.record_id,
        "fund_code": record.fund_code,
        "fund_name": fund_info.fund_name if fund_info else None,
        "record_type": record.record_type,
        "record_date": record.record_date,
        "signal_type": record.signal_type,
        "trigger_condition": record.trigger_condition,
        "trigger_value": record.trigger_value,
        "suggested_action": record.suggested_action,
        "exec_status": record.exec_status,
        "exec_date": record.exec_date,
        "actual_action": record.actual_action,
        "platform": record.platform,
        "amount": record.amount,
        "shares": record.shares,
        "nav": record.nav,
        "fee": record.fee,
        "note": record.note,
        "created_at": record.created_at,
    }


@router.post("")
def create_record(
    record: TradeRecordCreate,
    db: Session = Depends(get_db),
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
                rows = db.query(FundHolding.platform).filter(FundHolding.fund_code == record.fund_code).distinct().all()
                if len(rows) == 1:
                    platform = rows[0][0]
                elif len(rows) > 1:
                    raise HTTPException(status_code=400, detail="该基金存在多个平台持仓，请指定 platform")
                else:
                    raise HTTPException(status_code=400, detail="新交易记录必须指定 platform")

            # 卖出时校验可卖份额
            if record.record_type == "卖出":
                holding = db.query(FundHolding).filter(
                    FundHolding.fund_code == record.fund_code,
                    FundHolding.platform == platform
                ).first()
                if not holding or (holding.holding_shares or 0) <= 0:
                    raise HTTPException(status_code=400, detail="当前平台无可卖持仓")
                if record.shares > (holding.holding_shares or 0):
                    raise HTTPException(status_code=400, detail="卖出份额不能超过当前持仓份额")

        new_record = TradeRecord(
            fund_code=record.fund_code,
            record_type=record.record_type,
            record_date=record.record_date,
            platform=platform,
            signal_type=record.signal_type,
            trigger_condition=record.trigger_condition,
            trigger_value=record.trigger_value,
            suggested_action=record.suggested_action,
            exec_status=record.exec_status,
            exec_date=record.exec_date,
            actual_action=record.actual_action,
            amount=record.amount,
            shares=record.shares,
            nav=record.nav,
            fee=record.fee,
            note=record.note,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        db.add(new_record)

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
        db.refresh(new_record)
        return {"record_id": new_record.record_id, "message": "记录创建成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        import logging
        logging.getLogger(__name__).error("创建交易记录失败", exc_info=True)
        raise HTTPException(status_code=500, detail="记录创建失败")


@router.patch("/{record_id}")
def update_record(
    record_id: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    """更新交易记录（部分字段）"""
    record = db.query(TradeRecord).filter(TradeRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 允许更新的字段白名单
    allowed_fields = {
        "exec_status", "exec_date", "actual_action",
        "amount", "shares", "nav", "fee", "note",
    }

    updated = False
    for key, val in payload.items():
        if key in allowed_fields:
            setattr(record, key, val)
            updated = True

    if not updated:
        raise HTTPException(status_code=400, detail="没有可更新的字段")

    db.commit()
    return {"message": "记录已更新"}


@router.delete("/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    """删除交易记录"""
    record = db.query(TradeRecord).filter(TradeRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
        
    db.delete(record)
    db.commit()
    return {"message": "记录已删除"}
