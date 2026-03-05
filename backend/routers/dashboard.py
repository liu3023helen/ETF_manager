from fastapi import APIRouter, Depends
import sqlite3
from ..database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _calc_current_value(db: sqlite3.Connection):
    """计算每条持仓的当前市值。

    优先使用 daily_quotes 中最新净值 * 份额，
    若无净值数据则回退到 shares * cost_price。
    返回: list[dict] 包含 holding_id, fund_code, platform, fund_category, current_value
    """
    rows = db.execute(
        "SELECT h.holding_id, h.fund_code, h.platform, h.shares, h.cost_price, "
        "       h.total_invested, f.fund_category, "
        "       q.nav AS latest_nav, q.date AS nav_date "
        "FROM my_holdings h "
        "LEFT JOIN fund_info f ON h.fund_code = f.fund_code "
        "LEFT JOIN ("
        "    SELECT fund_code, nav, date FROM daily_quotes "
        "    WHERE (fund_code, date) IN ("
        "        SELECT fund_code, MAX(date) FROM daily_quotes GROUP BY fund_code"
        "    )"
        ") q ON h.fund_code = q.fund_code"
    ).fetchall()

    results = []
    for r in rows:
        shares = r["shares"] or 0
        cost_price = r["cost_price"] or 0
        latest_nav = r["latest_nav"]
        if latest_nav and latest_nav > 0:
            current_value = round(shares * latest_nav, 2)
        else:
            current_value = round(shares * cost_price, 2)
        results.append({
            "holding_id": r["holding_id"],
            "fund_code": r["fund_code"],
            "platform": r["platform"],
            "fund_category": r["fund_category"] or "其他",
            "total_invested": r["total_invested"] or 0,
            "current_value": current_value,
            "latest_nav": latest_nav,
            "nav_date": r["nav_date"],
        })
    return results


@router.get("/summary")
def get_summary(db: sqlite3.Connection = Depends(get_db)):
    holdings = _calc_current_value(db)

    total_assets = sum(h["current_value"] for h in holdings)
    total_invested = sum(h["total_invested"] for h in holdings)
    total_pnl = total_assets - total_invested
    pnl_rate = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    # 持仓基金数（仅统计 current_value > 0 的）
    fund_count = len(set(
        h["fund_code"] for h in holdings if h["current_value"] > 0
    ))

    # 按分类分布
    cat_map: dict[str, float] = {}
    for h in holdings:
        cat = h["fund_category"]
        cat_map[cat] = cat_map.get(cat, 0) + h["current_value"]
    category_distribution = sorted(
        [{"category": k, "value": round(v, 2)} for k, v in cat_map.items()],
        key=lambda x: x["value"], reverse=True,
    )

    # 按平台分布
    plat_map: dict[str, float] = {}
    for h in holdings:
        plat = h["platform"]
        plat_map[plat] = plat_map.get(plat, 0) + h["current_value"]
    platform_distribution = sorted(
        [{"platform": k, "value": round(v, 2)} for k, v in plat_map.items()],
        key=lambda x: x["value"], reverse=True,
    )

    # 待执行信号数
    pending_signals = db.execute(
        "SELECT COUNT(*) as cnt FROM trade_signals WHERE exec_status='待执行'"
    ).fetchone()["cnt"]

    return {
        "total_assets": round(total_assets, 2),
        "total_invested": round(total_invested, 2),
        "total_pnl": round(total_pnl, 2),
        "pnl_rate": round(pnl_rate, 2),
        "fund_count": fund_count,
        "category_distribution": category_distribution,
        "platform_distribution": platform_distribution,
        "pending_signals": pending_signals,
    }
