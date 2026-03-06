from pydantic import BaseModel
from typing import Optional, List


class FundInfo(BaseModel):
    fund_code: str
    fund_name: str
    fund_company: Optional[str] = None
    fund_type: Optional[str] = None
    tracking_index: Optional[str] = None
    risk_level: Optional[str] = None
    fund_category: Optional[str] = None
    top_holdings: Optional[str] = None
    risk_points: Optional[str] = None
    return_1y: Optional[str] = None
    return_3y: Optional[str] = None
    return_since_inception: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class HoldingDetail(BaseModel):
    holding_id: int
    fund_code: str
    fund_name: Optional[str] = None
    fund_category: Optional[str] = None
    platform: str
    shares: float = 0
    cost_price: float = 0
    base_shares: float = 0
    tradable_shares: float = 0
    total_invested: float = 0
    first_buy_date: Optional[str] = None
    updated_at: Optional[str] = None
    current_value: float = 0
    latest_nav: Optional[float] = None
    nav_date: Optional[str] = None
    risk_level: Optional[str] = None


class DailyQuote(BaseModel):
    id: Optional[int] = None
    fund_code: str
    fund_name: Optional[str] = None
    date: str
    nav: Optional[float] = None
    acc_nav: Optional[float] = None
    daily_change_pct: Optional[float] = None
    daily_value: Optional[float] = None
    daily_pnl: Optional[float] = None


class TradingRule(BaseModel):
    rule_id: Optional[int] = None
    fund_category: str
    rule_type: str
    condition_desc: str
    threshold: Optional[float] = None
    action_desc: str
    priority: int = 0
    is_active: int = 1


class TradingRuleCreate(BaseModel):
    fund_category: str
    rule_type: str
    condition_desc: str
    threshold: Optional[float] = None
    action_desc: str
    priority: int = 0


class TradeRecord(BaseModel):
    record_id: Optional[int] = None
    fund_code: str
    fund_name: Optional[str] = None
    record_type: Optional[str] = None
    record_date: Optional[str] = None
    signal_type: Optional[str] = None
    trigger_condition: Optional[str] = None
    trigger_value: Optional[float] = None
    suggested_action: Optional[str] = None
    exec_status: Optional[str] = None
    exec_date: Optional[str] = None
    actual_action: Optional[str] = None
    amount: Optional[float] = None
    shares: Optional[float] = None
    nav: Optional[float] = None
    fee: float = 0
    note: Optional[str] = None
    created_at: Optional[str] = None


class TradeRecordCreate(BaseModel):
    fund_code: str
    fund_name: Optional[str] = None
    record_type: str
    record_date: str
    signal_type: Optional[str] = None
    trigger_condition: Optional[str] = None
    trigger_value: Optional[float] = None
    suggested_action: Optional[str] = None
    exec_status: Optional[str] = "待执行"
    exec_date: Optional[str] = None
    actual_action: Optional[str] = None
    amount: Optional[float] = None
    shares: Optional[float] = None
    nav: Optional[float] = None
    fee: float = 0
    note: Optional[str] = None


class DashboardSummary(BaseModel):
    total_assets: float = 0
    total_invested: float = 0
    total_pnl: float = 0
    pnl_rate: float = 0
    fund_count: int = 0
    category_distribution: List[dict] = []
    platform_distribution: List[dict] = []
