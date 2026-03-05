from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from ..database import get_db
from ..models import TradingRuleCreate

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("")
def list_rules(
    category: str = None,
    rule_type: str = None,
    db: sqlite3.Connection = Depends(get_db),
):
    sql = "SELECT * FROM trading_rules WHERE 1=1"
    params = []
    if category:
        sql += " AND fund_category=?"
        params.append(category)
    if rule_type:
        sql += " AND rule_type=?"
        params.append(rule_type)
    sql += " ORDER BY fund_category, priority, rule_id"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.post("")
def create_rule(rule: TradingRuleCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute(
        "INSERT INTO trading_rules (fund_category, rule_type, condition_desc, threshold, action_desc, priority) "
        "VALUES (?,?,?,?,?,?)",
        (
            rule.fund_category,
            rule.rule_type,
            rule.condition_desc,
            rule.threshold,
            rule.action_desc,
            rule.priority,
        ),
    )
    db.commit()
    return {"rule_id": cursor.lastrowid, "message": "交易规则创建成功"}


@router.put("/{rule_id}")
def update_rule(
    rule_id: int, rule: TradingRuleCreate, db: sqlite3.Connection = Depends(get_db)
):
    db.execute(
        "UPDATE trading_rules SET fund_category=?, rule_type=?, condition_desc=?, "
        "threshold=?, action_desc=?, priority=? WHERE rule_id=?",
        (
            rule.fund_category,
            rule.rule_type,
            rule.condition_desc,
            rule.threshold,
            rule.action_desc,
            rule.priority,
            rule_id,
        ),
    )
    db.commit()
    return {"message": "交易规则更新成功"}


@router.patch("/{rule_id}/toggle")
def toggle_rule(rule_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute(
        "UPDATE trading_rules SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END "
        "WHERE rule_id=?",
        (rule_id,),
    )
    db.commit()
    return {"message": "交易规则状态已切换"}
