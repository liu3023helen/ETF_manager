from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from datetime import date
from ..database import get_db
from ..models import DcaPlanCreate, DcaPlanUpdate

router = APIRouter(prefix="/api/dca-plans", tags=["dca_plans"])


@router.get("")
def list_plans(active_only: bool = False, db: sqlite3.Connection = Depends(get_db)):
    sql = (
        "SELECT d.*, f.fund_name, f.fund_category FROM dca_plans d "
        "LEFT JOIN fund_info f ON d.fund_code=f.fund_code "
    )
    if active_only:
        sql += "WHERE d.end_date='9999-12-31' AND d.is_active=1 "
    sql += "ORDER BY d.end_date DESC, d.plan_id DESC"
    rows = db.execute(sql).fetchall()
    return [dict(r) for r in rows]


@router.post("")
def create_plan(plan: DcaPlanCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute(
        "INSERT INTO dca_plans (fund_code, platform, frequency, amount, dca_type, total_invested, start_date, end_date) "
        "VALUES (?,?,?,?,?,?,?,'9999-12-31')",
        (
            plan.fund_code,
            plan.platform,
            plan.frequency,
            plan.amount,
            plan.dca_type,
            plan.total_invested,
            plan.start_date or date.today().isoformat(),
        ),
    )
    db.commit()
    return {"plan_id": cursor.lastrowid, "message": "定投计划创建成功"}


@router.put("/{plan_id}")
def modify_plan(
    plan_id: int, plan: DcaPlanUpdate, db: sqlite3.Connection = Depends(get_db)
):
    """修改定投计划：结束旧计划 + 创建新计划（只增不减）"""
    old = db.execute(
        "SELECT * FROM dca_plans WHERE plan_id=?", (plan_id,)
    ).fetchone()
    if not old:
        raise HTTPException(status_code=404, detail="定投计划不存在")
    if old["end_date"] != "9999-12-31":
        raise HTTPException(status_code=400, detail="该计划已结束，不可修改")

    today = date.today().isoformat()

    # 1. 结束旧计划
    db.execute(
        "UPDATE dca_plans SET end_date=?, is_active=0 WHERE plan_id=?",
        (today, plan_id),
    )

    # 2. 创建新计划，未提供的字段继承旧值
    new_fund_code = plan.fund_code or old["fund_code"]
    new_platform = plan.platform or old["platform"]
    new_frequency = plan.frequency or old["frequency"]
    new_amount = plan.amount if plan.amount is not None else old["amount"]
    new_dca_type = plan.dca_type or old["dca_type"]
    new_start_date = plan.start_date or today

    cursor = db.execute(
        "INSERT INTO dca_plans (fund_code, platform, frequency, amount, dca_type, total_invested, start_date, end_date, is_active) "
        "VALUES (?,?,?,?,?,0,?,'9999-12-31',1)",
        (new_fund_code, new_platform, new_frequency, new_amount, new_dca_type, new_start_date),
    )
    db.commit()
    return {
        "old_plan_id": plan_id,
        "new_plan_id": cursor.lastrowid,
        "message": "定投计划已修改（旧计划结束，新计划创建）",
    }


@router.patch("/{plan_id}/toggle")
def toggle_plan(plan_id: int, db: sqlite3.Connection = Depends(get_db)):
    """暂停/恢复定投计划（不改end_date，只切换is_active）"""
    old = db.execute(
        "SELECT * FROM dca_plans WHERE plan_id=?", (plan_id,)
    ).fetchone()
    if not old:
        raise HTTPException(status_code=404, detail="定投计划不存在")
    if old["end_date"] != "9999-12-31":
        raise HTTPException(status_code=400, detail="该计划已结束，不可操作")

    db.execute(
        "UPDATE dca_plans SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END "
        "WHERE plan_id=?",
        (plan_id,),
    )
    db.commit()
    return {"message": "定投计划状态已切换"}


@router.patch("/{plan_id}/stop")
def stop_plan(plan_id: int, db: sqlite3.Connection = Depends(get_db)):
    """彻底结束定投计划（end_date改为今天）"""
    old = db.execute(
        "SELECT * FROM dca_plans WHERE plan_id=?", (plan_id,)
    ).fetchone()
    if not old:
        raise HTTPException(status_code=404, detail="定投计划不存在")
    if old["end_date"] != "9999-12-31":
        raise HTTPException(status_code=400, detail="该计划已结束")

    today = date.today().isoformat()
    db.execute(
        "UPDATE dca_plans SET end_date=?, is_active=0 WHERE plan_id=?",
        (today, plan_id),
    )
    db.commit()
    return {"message": f"定投计划已结束，结束日期: {today}"}
