from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import TradingRule
from ..schemas import TradingRule as TradingRuleSchema, TradingRuleCreate

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=List[TradingRuleSchema])
def list_rules(
    category: str = None,
    rule_type: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(TradingRule)
    if category:
        query = query.filter(TradingRule.fund_category == category)
    if rule_type:
        query = query.filter(TradingRule.rule_type == rule_type)
        
    query = query.order_by(TradingRule.fund_category, TradingRule.priority, TradingRule.rule_id)
    return query.all()


@router.post("")
def create_rule(rule: TradingRuleCreate, db: Session = Depends(get_db)):
    new_rule = TradingRule(
        fund_category=rule.fund_category,
        rule_type=rule.rule_type,
        condition_desc=rule.condition_desc,
        threshold=rule.threshold,
        action_desc=rule.action_desc,
        priority=rule.priority,
        is_active=1
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return {"rule_id": new_rule.rule_id, "message": "交易规则创建成功"}


@router.put("/{rule_id}")
def update_rule(
    rule_id: int, rule: TradingRuleCreate, db: Session = Depends(get_db)
):
    existing_rule = db.query(TradingRule).filter(TradingRule.rule_id == rule_id).first()
    if not existing_rule:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
        
    existing_rule.fund_category = rule.fund_category
    existing_rule.rule_type = rule.rule_type
    existing_rule.condition_desc = rule.condition_desc
    existing_rule.threshold = rule.threshold
    existing_rule.action_desc = rule.action_desc
    existing_rule.priority = rule.priority
    
    db.commit()
    return {"message": "交易规则更新成功"}


@router.patch("/{rule_id}/toggle")
def toggle_rule(rule_id: int, db: Session = Depends(get_db)):
    existing_rule = db.query(TradingRule).filter(TradingRule.rule_id == rule_id).first()
    if not existing_rule:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
        
    existing_rule.is_active = 0 if existing_rule.is_active == 1 else 1
    db.commit()
    return {"message": "交易规则状态已切换"}
