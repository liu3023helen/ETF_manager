"""
数据库迁移脚本 v2：
1. fund_info 加 updated_at 字段
2. my_holdings 加 latest_nav、nav_date 字段，重排 holding_id
3. dca_plans 加 end_date 字段
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "etf_manager.db")


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF;")

    changes = []

    # === 1. fund_info: 加 updated_at ===
    if not column_exists(cursor, "fund_info", "updated_at"):
        cursor.execute("ALTER TABLE fund_info ADD COLUMN updated_at TEXT")
        cursor.execute("UPDATE fund_info SET updated_at = COALESCE(created_at, datetime('now', 'localtime'))")
        changes.append("fund_info: added updated_at")

    # === 2. my_holdings: 加 latest_nav, nav_date ===
    if not column_exists(cursor, "my_holdings", "latest_nav"):
        cursor.execute("ALTER TABLE my_holdings ADD COLUMN latest_nav REAL DEFAULT 0")
        changes.append("my_holdings: added latest_nav")

    if not column_exists(cursor, "my_holdings", "nav_date"):
        cursor.execute("ALTER TABLE my_holdings ADD COLUMN nav_date TEXT")
        changes.append("my_holdings: added nav_date")

    # === 3. my_holdings: 重排 holding_id 保持连续 ===
    rows = cursor.execute("SELECT holding_id FROM my_holdings ORDER BY fund_code, platform").fetchall()
    for new_id, row in enumerate(rows, start=1):
        if row["holding_id"] != new_id:
            cursor.execute("UPDATE my_holdings SET holding_id=? WHERE holding_id=?", (-new_id, row["holding_id"]))
    cursor.execute("UPDATE my_holdings SET holding_id = -holding_id WHERE holding_id < 0")
    changes.append(f"my_holdings: reindexed {len(rows)} rows")

    # === 4. dca_plans: 加 end_date ===
    if not column_exists(cursor, "dca_plans", "end_date"):
        cursor.execute("ALTER TABLE dca_plans ADD COLUMN end_date TEXT DEFAULT '9999-12-31'")
        cursor.execute("UPDATE dca_plans SET end_date = '9999-12-31' WHERE end_date IS NULL")
        changes.append("dca_plans: added end_date")

    # === 5. dca_plans 索引 ===
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dca_plans_active ON dca_plans(end_date, is_active)")
    changes.append("dca_plans: created index idx_dca_plans_active")

    conn.commit()

    # 验证
    print(f"Migration completed on: {DB_PATH}")
    print(f"Changes: {len(changes)}")
    for c in changes:
        print(f"  - {c}")

    # 打印结果
    for table in ["fund_info", "my_holdings", "dca_plans"]:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cursor.fetchall()]
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"\n  [{table}] {count} rows, columns: {', '.join(cols)}")

    conn.close()


if __name__ == "__main__":
    migrate()
