from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class FundInfo(Base):
    __tablename__ = "fund_info"

    fund_code = Column(String, primary_key=True)
    fund_name = Column(String, nullable=False)
    fund_company = Column(String, nullable=True)
    fund_type = Column(String, nullable=True)
    tracking_index = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)
    fund_category = Column(String, nullable=True)
    top_holdings = Column(String, nullable=True)
    risk_points = Column(String, nullable=True)
    return_1y = Column(String, nullable=True)
    return_3y = Column(String, nullable=True)
    return_since_inception = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)
    inception_date = Column(String, nullable=True)

    # Relationships
    holdings = relationship("FundHolding", back_populates="fund", cascade="all, delete-orphan")
    trade_records = relationship("TradeRecord", back_populates="fund", cascade="all, delete-orphan")
    daily_quotes = relationship("DailyQuote", back_populates="fund", cascade="all, delete-orphan")


class FundHolding(Base):
    __tablename__ = "fund_holdings"

    holding_id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String, ForeignKey("fund_info.fund_code"), nullable=False, index=True)
    platform = Column(String, nullable=True)
    holding_shares = Column(Float, nullable=True)
    avg_buy_price = Column(Float, nullable=True)
    base_shares = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    holding_value = Column(Float, nullable=True)
    invested_capital = Column(Float, nullable=True)
    profit_loss_amount = Column(Float, nullable=True)
    return_rate = Column(Float, nullable=True)
    
    dca_is_active = Column(Integer, nullable=True)
    dca_frequency = Column(String, nullable=True)
    dca_amount = Column(Float, nullable=True)
    dca_type = Column(String, nullable=True)
    dca_total_invested = Column(Float, nullable=True)
    
    first_buy_date = Column(String, nullable=True)
    last_update_date = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)

    # Relationship
    fund = relationship("FundInfo", back_populates="holdings")


class TradeRecord(Base):
    __tablename__ = "trade_records"

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String, ForeignKey("fund_info.fund_code"), nullable=False, index=True)
    record_type = Column(String, index=True)
    record_date = Column(String, index=True)
    signal_type = Column(String, nullable=True)
    trigger_condition = Column(String, nullable=True)
    trigger_value = Column(Float, nullable=True)
    suggested_action = Column(String, nullable=True)
    exec_status = Column(String, default='待执行', index=True)
    exec_date = Column(String, nullable=True)
    actual_action = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    shares = Column(Float, nullable=True)
    nav = Column(Float, nullable=True)
    fee = Column(Float, default=0.0)
    note = Column(String, nullable=True)
    created_at = Column(String, nullable=True)

    # Relationship
    fund = relationship("FundInfo", back_populates="trade_records")


class DailyQuote(Base):
    __tablename__ = "daily_quotes"

    quote_id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String, ForeignKey("fund_info.fund_code"), nullable=False, index=True)
    quote_date = Column(String, nullable=False)
    open_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=True)
    acc_nav = Column(Float, nullable=True)
    created_at = Column(String, nullable=True)

    # Ensure unique constraint (fund_code, quote_date)
    __table_args__ = (
        UniqueConstraint('fund_code', 'quote_date', name='uq_daily_quotes_fund_date'),
    )

    # Relationship
    fund = relationship("FundInfo", back_populates="daily_quotes")


class TradingRule(Base):
    __tablename__ = "trading_rules"

    rule_id = Column(Integer, primary_key=True, autoincrement=True)
    fund_category = Column(String, index=True)
    rule_type = Column(String, index=True)
    condition_desc = Column(String, nullable=True)
    threshold = Column(Float, nullable=True)
    action_desc = Column(String, nullable=True)
    priority = Column(Integer, nullable=True)
    is_active = Column(Integer, index=True, default=1)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)
