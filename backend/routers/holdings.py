from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from ..database import get_db

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


def reindex_holdings(db: sqlite3.Connection):
    """重排 holding_id，保持从1开始连续不断"""
    rows = db.execute(
        "SELECT holding_id FROM fund_holdings ORDER BY fund_code, platform"
    ).fetchall()
    for new_id, row in enumerate(rows, start=1):
        if row["holding_id"] != new_id:
            db.execute(
                "UPDATE fund_holdings SET holding_id=? WHERE holding_id=?",
                (-new_id, row["holding_id"]),
            )
    # 负数转正（避免两阶段冲突）
    db.execute(
        "UPDATE fund_holdings SET holding_id = -holding_id WHERE holding_id < 0"
    )
    db.commit()


@router.get("")
def list_holdings(platform: str = None, db: sqlite3.Connection = Depends(get_db)):
    sql = (
        "SELECT h.holding_id, h.fund_code, h.fund_name, h.platform, "
        "       h.holding_shares as shares, h.avg_buy_price as cost_price, h.base_shares, "
        "       h.invested_capital as total_invested, h.first_buy_date, h.updated_at, "
        "       h.holding_value, h.profit_loss_amount, h.return_rate, "
        "       h.dca_is_active, h.dca_frequency, h.dca_amount, h.dca_type, h.dca_total_invested, "
        "       f.fund_name AS fi_fund_name, f.fund_category, f.risk_level, "
        "       q.nav AS latest_nav, q.date AS nav_date "
        "FROM fund_holdings h "
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
        holding_value = item.get("holding_value")
        total_invested = item.get("total_invested") or 0
        
        # 计算可用份额
        base_shares = item.get("base_shares") or 0
        item["tradable_shares"] = round(shares - base_shares, 2)

        current_value = 0
        if latest_nav and latest_nav > 0:
            current_value = round(shares * latest_nav, 2)
            # 重算盈亏和收益率，覆盖表里的静态值，确保展示最新数据
            item["holding_value"] = current_value
            item["current_price"] = latest_nav
            item["profit_loss_amount"] = round(current_value - total_invested, 2)
            if total_invested > 0:
                item["return_rate"] = round((current_value - total_invested) / total_invested * 100, 2)
            else:
                item["return_rate"] = 0
        elif holding_value and holding_value > 0:
             current_value = holding_value
        else:
            current_value = round(shares * cost_price, 2)
        
        item["current_value"] = current_value
        results.append(item)
    return results


@router.get("/{holding_id}")
def get_holding(holding_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT h.*, h.holding_shares as shares, h.avg_buy_price as cost_price, "
        "       h.invested_capital as total_invested, "
        "       f.fund_name AS fi_fund_name, f.fund_category, f.risk_level "
        "FROM fund_holdings h "
        "LEFT JOIN fund_info f ON h.fund_code = f.fund_code "
        "WHERE h.holding_id=?",
        (holding_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="持仓记录不存在")
    item = dict(row)
    item["fund_name"] = item.pop("fi_fund_name", None) or item.get("fund_name")
    
    # 补充 tradable_shares
    shares = item.get("shares") or 0
    base_shares = item.get("base_shares") or 0
    item["tradable_shares"] = round(shares - base_shares, 2)
    
    return item


@router.delete("/{holding_id}")
def delete_holding(holding_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT holding_id FROM fund_holdings WHERE holding_id=?", (holding_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="持仓记录不存在")
    db.execute("DELETE FROM fund_holdings WHERE holding_id=?", (holding_id,))
    reindex_holdings(db)
    return {"message": "持仓记录已删除"}
