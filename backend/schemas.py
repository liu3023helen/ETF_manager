from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal

class FundInfoBase(BaseModel):
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
    inception_date: Optional[str] = None

class FundInfo(FundInfoBase):
    model_config = ConfigDict(from_attributes=True)

class HoldingDetail(BaseModel):
    holding_id: int
    fund_code: str
    fund_name: Optional[str] = None
    fund_category: Optional[str] = None
    platform: Optional[str] = None
    holding_shares: float = Field(default=0, alias="shares")  # Alias for frontend
    avg_buy_price: float = Field(default=0, alias="cost_price")
    base_shares: float = 0
    tradable_shares: float = 0  # Assuming it's calculated
    invested_capital: float = Field(default=0, alias="total_invested")
    first_buy_date: Optional[str] = None
    updated_at: Optional[str] = None
    current_value: float = Field(default=0)  # Calculated or from DB
    current_price: Optional[float] = Field(default=None, alias="latest_nav")
    last_update_date: Optional[str] = Field(default=None, alias="nav_date")
    risk_level: Optional[str] = None
    
    # 盈亏相关
    holding_value: Optional[float] = None
    profit_loss_amount: Optional[float] = None
    return_rate: Optional[float] = None

    # Optional DCA fields
    dca_is_active: Optional[int] = None
    dca_frequency: Optional[str] = None
    dca_amount: Optional[float] = None
    dca_type: Optional[str] = None
    dca_total_invested: Optional[float] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DailyQuote(BaseModel):
    quote_id: Optional[int] = Field(default=None, alias="id")
    fund_code: str
    fund_name: Optional[str] = None
    quote_date: str = Field(alias="date")
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = Field(default=None, alias="nav")
    acc_nav: Optional[float] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TradingRule(BaseModel):
    rule_id: Optional[int] = None
    fund_category: str
    rule_type: str
    condition_desc: str
    threshold: Optional[float] = None
    action_desc: str
    priority: int = 0
    is_active: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


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
    platform: Optional[str] = None
    amount: Optional[float] = None
    shares: Optional[float] = None
    nav: Optional[float] = None
    fee: float = 0
    note: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TradeRecordCreate(BaseModel):
    fund_code: str
    fund_name: Optional[str] = None
    record_type: Literal["买入", "卖出", "定投", "信号"]
    record_date: str
    platform: Optional[str] = None
    signal_type: Optional[str] = None
    trigger_condition: Optional[str] = None
    trigger_value: Optional[float] = Field(default=None)
    suggested_action: Optional[str] = None
    exec_status: Optional[Literal["待执行", "已执行", "已忽略"]] = "待执行"
    exec_date: Optional[str] = None
    actual_action: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    shares: Optional[float] = Field(default=None, ge=0)
    nav: Optional[float] = Field(default=None, ge=0)
    fee: float = Field(default=0, ge=0)
    note: Optional[str] = None

class DashboardSummary(BaseModel):
    total_assets: float = 0
    total_invested: float = 0
    total_pnl: float = 0
    pnl_rate: float = 0
    fund_count: int = 0
    category_distribution: List[dict] = []
    platform_distribution: List[dict] = []
    pending_records: int = 0
