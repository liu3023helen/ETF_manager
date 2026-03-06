from fastapi import APIRouter, Body, Depends, HTTPException, Query
from typing import Optional
import re
import sqlite3


from ..database import get_db

router = APIRouter(prefix="/api/tables", tags=["tables"])

# 白名单：只允许查询这些“展示表名”（前端看到的名字）
ALLOWED_TABLES = {
    "fund_info": "基金信息",
    "fund_holdings": "持仓管理",
    "daily_quotes": "每日净值",
    "dca_plans": "定投计划",
    "transactions": "交易记录",
    "trading_rules": "交易规则",
    "trade_signals": "交易信号",
}

# 展示名 -> 真实物理表名 映射（保留历史兼容）
TABLE_NAME_MAP = {
    # 之前 fund_holdings 映射到 my_holdings，现已直接使用 fund_holdings 表
}


# 每个表的默认排序规则（按展示名配置）
DEFAULT_SORT = {
    "fund_info": "fund_code ASC",
    "fund_holdings": "fund_code ASC",
    "daily_quotes": "date ASC, fund_code ASC",
    "trading_rules": "fund_category ASC, rule_type ASC, priority ASC, rule_id ASC",
}


MAX_SQL_ROWS = 500
FORBIDDEN_SQL_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "vacuum",
    "reindex",
    "pragma",
}


def resolve_physical_table(display_table_name: str, conn: Optional[sqlite3.Connection] = None) -> str:
    """将前端展示表名解析为数据库真实表名。"""
    # fund_holdings 优先使用物理新表；不存在时回退到历史 my_holdings
    if display_table_name == "fund_holdings":
        if conn is not None and table_exists(conn, "fund_holdings"):
            return "fund_holdings"
        return "my_holdings"
    return TABLE_NAME_MAP.get(display_table_name, display_table_name)



def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table_name,),
    )
    return cursor.fetchone() is not None


def sanitize_identifier(identifier: str) -> str:
    """仅允许安全的 SQLite 标识符（表名）。"""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise HTTPException(status_code=400, detail=f"非法表名: {identifier}")
    return identifier


def normalize_sql(sql: str) -> str:
    """清理 SQL：移除注释、去除前后空白与末尾分号。"""
    # 移除 -- 注释，兼容多行输入
    lines = []
    for line in sql.splitlines():
        line = line.split("--", 1)[0].strip()
        if line:
            lines.append(line)

    normalized = " ".join(lines).strip()

    while normalized.endswith(";"):
        normalized = normalized[:-1].strip()
    return normalized




@router.get("")
def list_tables(conn: sqlite3.Connection = Depends(get_db)):

    """获取所有可查看的表及其记录数

    注意：有些表在白名单中但可能尚未创建（例如尚未启用的功能模块），
    对于不存在的表，这里会自动跳过，防止接口 500。
    """
    result = []
    for display_table_name, label in ALLOWED_TABLES.items():
        physical_table_name = resolve_physical_table(display_table_name, conn)
        try:

            cursor = conn.execute(f"SELECT COUNT(*) FROM [{physical_table_name}]")
            count = cursor.fetchone()[0]

            cursor = conn.execute(f"PRAGMA table_info([{physical_table_name}])")
            columns = [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # 表不存在或结构异常时，直接跳过该表
            continue

        result.append({
            "name": display_table_name,
            "label": label,
            "count": count,
            "columns": columns,
            "default_sort": DEFAULT_SORT.get(display_table_name),
        })
    return result




@router.post("/execute-sql")
def execute_sql(
    payload: dict = Body(...),
    conn: sqlite3.Connection = Depends(get_db),
):
    """执行只读 SQL（仅支持 SELECT / DESC）。"""
    raw_sql = str(payload.get("sql", ""))
    sql = normalize_sql(raw_sql)

    if not sql:
        raise HTTPException(status_code=400, detail="SQL 不能为空")

    if ";" in sql:
        raise HTTPException(status_code=400, detail="一次仅允许执行一条 SQL")

    # 兼容 MySQL 风格 desc fund_info
    desc_match = re.fullmatch(r"(?i)desc\s+([A-Za-z_][A-Za-z0-9_]*)", sql)
    if desc_match:
        display_table_name = sanitize_identifier(desc_match.group(1))
        physical_table_name = resolve_physical_table(display_table_name)

        if (
            display_table_name not in ALLOWED_TABLES
            and physical_table_name not in TABLE_NAME_MAP.values()
        ):
            raise HTTPException(status_code=400, detail=f"不允许访问表: {display_table_name}")

        if not table_exists(conn, physical_table_name):
            raise HTTPException(status_code=404, detail=f"表不存在: {display_table_name}")

        cursor = conn.execute(f"PRAGMA table_info([{physical_table_name}])")
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return {
            "sql": raw_sql,
            "executed_sql": f"PRAGMA table_info({physical_table_name})",
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": False,
        }

    # 只允许 SELECT
    if not re.match(r"(?is)^select\b", sql):
        raise HTTPException(status_code=400, detail="仅允许执行 SELECT 或 DESC 查询")

    # 阻止危险关键字（防止绕过）
    lowered_sql = sql.lower()
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered_sql):
            raise HTTPException(status_code=400, detail=f"禁止的 SQL 关键字: {keyword}")

    # 表名白名单校验：校验 FROM / JOIN 中出现的表
    referenced_tables = re.findall(r"(?i)\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_]*)\b", sql)
    sql_for_exec = sql

    for table_name in referenced_tables:
        safe_table_name = sanitize_identifier(table_name)
        physical_table_name = resolve_physical_table(safe_table_name, conn)


        # 允许使用展示名（fund_holdings）或物理名（my_holdings）
        if safe_table_name in ALLOWED_TABLES:
            pass
        elif physical_table_name in ALLOWED_TABLES or safe_table_name in TABLE_NAME_MAP.values():
            pass
        else:
            raise HTTPException(status_code=400, detail=f"不允许访问表: {safe_table_name}")

        if not table_exists(conn, physical_table_name):
            raise HTTPException(status_code=404, detail=f"表不存在: {safe_table_name}")

        # 将展示名替换为真实表名，防止 SQL 执行报错
        if safe_table_name != physical_table_name:
            sql_for_exec = re.sub(
                rf"(?i)\b{safe_table_name}\b",
                physical_table_name,
                sql_for_exec,
            )

    # 统一限制返回条数，避免一次查询过大
    has_limit = re.search(r"(?i)\blimit\s+\d+", sql_for_exec) is not None
    if not has_limit:
        sql_for_exec = f"{sql_for_exec} LIMIT {MAX_SQL_ROWS}"

    try:
        cursor = conn.execute(sql_for_exec)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=400, detail=f"SQL 执行失败: {str(e)}")

    return {
        "sql": raw_sql,
        "executed_sql": sql_for_exec,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": not has_limit and len(rows) >= MAX_SQL_ROWS,
    }


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
        raise HTTPException(status_code=400, detail=f"不允许访问表: {table_name}")

    physical_table_name = resolve_physical_table(table_name, conn)


    try:
        # 获取总记录数
        cursor = conn.execute(f"SELECT COUNT(*) FROM [{physical_table_name}]")
        total = cursor.fetchone()[0]

        # 获取列信息用于排序验证（保持表定义顺序）
        cursor = conn.execute(f"PRAGMA table_info([{physical_table_name}])")
        column_info = cursor.fetchall()
    except sqlite3.OperationalError:
        raise HTTPException(status_code=404, detail=f"表不存在: {table_name}")

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
            f"FROM [{physical_table_name}] {order_clause} LIMIT ? OFFSET ?"
        )
    else:
        query = f"SELECT * FROM [{physical_table_name}] {order_clause} LIMIT ? OFFSET ?"

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


