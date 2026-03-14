"""资产快照 API：提供收益曲线数据"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from ..database import get_db
from ..models import PortfolioSnapshot

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.get("")
def list_snapshots(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """查询资产快照列表（用于收益曲线）"""
    q = db.query(PortfolioSnapshot)
    if date_from:
        q = q.filter(PortfolioSnapshot.snapshot_date >= date_from)
    if date_to:
        q = q.filter(PortfolioSnapshot.snapshot_date <= date_to)
    rows = q.order_by(PortfolioSnapshot.snapshot_date.asc()).all()

    return [
        {
            "date": r.snapshot_date,
            "total_assets": round(r.total_assets, 2),
            "total_invested": round(r.total_invested, 2),
            "total_pnl": round(r.total_pnl, 2),
            "pnl_rate": round(r.pnl_rate, 2),
            "realized_pnl": round(r.realized_pnl or 0, 2),
            "fund_count": r.fund_count,
        }
        for r in rows
    ]


@router.get("/summary")
def snapshot_summary(db: Session = Depends(get_db)):
    """获取收益汇总指标（最新快照 vs 各时间段对比）"""
    latest = db.query(PortfolioSnapshot).order_by(
        PortfolioSnapshot.snapshot_date.desc()
    ).first()

    if not latest:
        return {
            "latest": None,
            "periods": [],
        }

    latest_data = {
        "date": latest.snapshot_date,
        "total_assets": round(latest.total_assets, 2),
        "total_invested": round(latest.total_invested, 2),
        "total_pnl": round(latest.total_pnl, 2),
        "pnl_rate": round(latest.pnl_rate, 2),
        "realized_pnl": round(latest.realized_pnl or 0, 2),
        "fund_count": latest.fund_count,
    }

    # 计算各时间段收益
    today = datetime.strptime(latest.snapshot_date, '%Y-%m-%d')
    periods = []

    for label, days in [("近1周", 7), ("近1月", 30), ("近3月", 90), ("近6月", 180), ("近1年", 365)]:
        target_date = (today - timedelta(days=days)).strftime('%Y-%m-%d')
        past = db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.snapshot_date >= target_date
        ).order_by(PortfolioSnapshot.snapshot_date.asc()).first()

        if past and past.total_assets > 0:
            pnl_change = latest.total_assets - past.total_assets
            pnl_rate_change = round((pnl_change / past.total_assets) * 100, 2)
            periods.append({
                "label": label,
                "pnl_change": round(pnl_change, 2),
                "pnl_rate_change": pnl_rate_change,
                "start_date": past.snapshot_date,
            })

    return {
        "latest": latest_data,
        "periods": periods,
    }
