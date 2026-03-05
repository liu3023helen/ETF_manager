from fastapi import APIRouter, Depends, Query
from typing import Optional
import sqlite3

from ..database import get_db

router = APIRouter(prefix="/api/tables", tags=["tables"])

# 白名单：只允许查询这些表
ALLOWED_TABLES = {
    "fund_info": "基金信息",
    "my_holdings": "持仓管理",
    "daily_quotes": "每日净值",
    "dca_plans": "定投计划",
    "transactions": "交易记录",
    "trading_rules": "交易规则",
    "trade_signals": "交易信号",
}

# 每个表的默认排序规则
DEFAULT_SORT = {
    "fund_info": "fund_code ASC",
    "my_holdings": "fund_code ASC",
    "daily_quotes": "date ASC, fund_code ASC",
}


@router.get("")
def list_tables(conn: sqlite3.Connection = Depends(get_db)):
    """获取所有可查看的表及其记录数"""
    result = []
    for table_name, label in ALLOWED_TABLES.items():
        cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        count = cursor.fetchone()[0]

        cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
        columns = [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]

        result.append({
            "name": table_name,
            "label": label,
            "count": count,
            "columns": columns,
            "default_sort": DEFAULT_SORT.get(table_name),
        })
    return result


@router.get("/{table_name}")
def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = Query(None, regex="^(asc|desc)$"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取指定表的数据（分页）"""
    if table_name not in ALLOWED_TABLES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"不允许访问表: {table_name}")

    # 获取总记录数
    cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    total = cursor.fetchone()[0]

    # 获取列信息用于排序验证（保持表定义顺序）
    cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
    column_info = cursor.fetchall()
    valid_columns = {row[1] for row in column_info}
    ordered_columns = [row[1] for row in column_info]

    # 确定排序方式：用户指定 > 默认排序
    if sort_by and sort_by in valid_columns:
        direction = "DESC" if sort_order == "desc" else "ASC"
        order_clause = f"ORDER BY [{sort_by}] {direction}"
        # daily_quotes 按 date 排序时，追加 fund_code 作为次级排序
        if table_name == "daily_quotes" and sort_by == "date":
            order_clause += ", [fund_code] ASC"
    elif table_name in DEFAULT_SORT:
        order_clause = f"ORDER BY {DEFAULT_SORT[table_name]}"
    else:
        order_clause = ""

    # 分页
    offset = (page - 1) * page_size

    # daily_quotes 表：用 ROW_NUMBER() 生成连续递增的 id，替代原始 id
    if table_name == "daily_quotes":
        non_id_cols = [c for c in ordered_columns if c != "id"]
        cols_str = ", ".join(f"[{c}]" for c in non_id_cols)
        query = (
            f"SELECT ROW_NUMBER() OVER ({order_clause}) AS id, {cols_str} "
            f"FROM [{table_name}] {order_clause} LIMIT ? OFFSET ?"
        )
    else:
        query = f"SELECT * FROM [{table_name}] {order_clause} LIMIT ? OFFSET ?"

    cursor = conn.execute(query, (page_size, offset))
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # daily_quotes 的 id 基于分页偏移量重新计算，确保跨页连续
    if table_name == "daily_quotes":
        for i, row in enumerate(rows):
            row["id"] = offset + i + 1

    return {
        "table_name": table_name,
        "label": ALLOWED_TABLES[table_name],
        "total": total,
        "page": page,
        "page_size": page_size,
        "columns": columns,
        "data": rows,
    }
