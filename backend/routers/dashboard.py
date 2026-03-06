from fastapi import APIRouter, Depends
import sqlite3
from ..database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_summary(db: sqlite3.Connection = Depends(get_db)):
    # 总资产、总投入、总盈亏
    row = db.execute(
        "SELECT COALESCE(SUM(holding_value), 0) as total_assets, "
        "COALESCE(SUM(invested_capital), 0) as total_invested, "
        "COALESCE(SUM(profit_loss_amount), 0) as total_pnl "
        "FROM fund_holdings"
    ).fetchone()

    total_assets = row["total_assets"]
    total_invested = row["total_invested"]
    total_pnl = row["total_pnl"]
    pnl_rate = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    # 持仓基金数
    fund_count = db.execute(
        "SELECT COUNT(DISTINCT fund_code) as cnt FROM fund_holdings WHERE holding_shares > 0"
    ).fetchone()["cnt"]

    # 按分类分布 (市值)
    cat_rows = db.execute(
        "SELECT COALESCE(f.fund_category, '其他') as category, "
        "SUM(h.holding_value) as value "
        "FROM fund_holdings h LEFT JOIN fund_info f ON h.fund_code=f.fund_code "
        "GROUP BY f.fund_category ORDER BY value DESC"
    ).fetchall()
    category_distribution = [
        {"category": r["category"] or "其他", "value": round(r["value"] or 0, 2)}
        for r in cat_rows
    ]

    # 按平台分布 (市值)
    plat_rows = db.execute(
        "SELECT platform, SUM(holding_value) as value "
        "FROM fund_holdings GROUP BY platform ORDER BY value DESC"
    ).fetchall()
    platform_distribution = [
        {"platform": r["platform"], "value": round(r["value"] or 0, 2)}
        for r in plat_rows
    ]

    # 待执行记录数
    try:
        pending_count = db.execute(
            "SELECT COUNT(*) as cnt FROM trade_records WHERE exec_status='待执行'"
        ).fetchone()["cnt"]
    except sqlite3.OperationalError:
        pending_count = 0

    return {
        "total_assets": round(total_assets, 2),
        "total_invested": round(total_invested, 2),
        "total_pnl": round(total_pnl, 2),
        "pnl_rate": round(pnl_rate, 2),
        "fund_count": fund_count,
        "category_distribution": category_distribution,
        "platform_distribution": platform_distribution,
        "pending_records": pending_count,
    }
