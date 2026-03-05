from fastapi import APIRouter, Depends
import sqlite3
from ..database import get_db

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


def reindex_holdings(db: sqlite3.Connection):
    """重排 holding_id，保持从1开始连续不断"""
    rows = db.execute(
        "SELECT holding_id FROM my_holdings ORDER BY fund_code, platform"
    ).fetchall()
    for new_id, row in enumerate(rows, start=1):
        if row["holding_id"] != new_id:
            db.execute(
                "UPDATE my_holdings SET holding_id=? WHERE holding_id=?",
                (-new_id, row["holding_id"]),
            )
    # 负数转正（避免两阶段冲突）
    db.execute(
        "UPDATE my_holdings SET holding_id = -holding_id WHERE holding_id < 0"
    )
    db.commit()


@router.get("")
def list_holdings(platform: str = None, db: sqlite3.Connection = Depends(get_db)):
    sql = (
        "SELECT h.holding_id, h.fund_code, h.fund_name, h.platform, "
        "       h.shares, h.cost_price, h.base_shares, h.tradable_shares, "
        "       h.total_invested, h.first_buy_date, h.updated_at, "
        "       f.fund_name AS fi_fund_name, f.fund_category, f.risk_level, "
        "       q.nav AS latest_nav, q.date AS nav_date "
        "FROM my_holdings h "
        "LEFT JOIN fund_info f ON h.fund_code = f.fund_code "
        "LEFT JOIN ("
        "    SELECT fund_code, nav, date FROM daily_quotes "
        "    WHERE (fund_code, date) IN ("
        "        SELECT fund_code, MAX(date) FROM daily_quotes GROUP BY fund_code"
        "    )"
        ") q ON h.fund_code = q.fund_code"
    )
    params = []
    if platform:
        sql += " WHERE h.platform=?"
        params.append(platform)
    sql += " ORDER BY h.holding_id"
    rows = db.execute(sql, params).fetchall()

    results = []
    for r in rows:
        item = dict(r)
        # 优先使用 fund_info 的名称
        item["fund_name"] = item.pop("fi_fund_name", None) or item.get("fund_name")
        # 动态计算当前市值
        shares = item.get("shares") or 0
        cost_price = item.get("cost_price") or 0
        latest_nav = item.get("latest_nav")
        if latest_nav and latest_nav > 0:
            item["current_value"] = round(shares * latest_nav, 2)
        else:
            item["current_value"] = round(shares * cost_price, 2)
        results.append(item)
    return results
