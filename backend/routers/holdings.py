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
        "SELECT h.*, f.fund_name, f.fund_category, f.risk_level "
        "FROM my_holdings h "
        "LEFT JOIN fund_info f ON h.fund_code=f.fund_code"
    )
    params = []
    if platform:
        sql += " WHERE h.platform=?"
        params.append(platform)
    sql += " ORDER BY h.holding_id"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
