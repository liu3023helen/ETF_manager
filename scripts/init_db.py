"""
ETF管理系统 - 数据库初始化脚本
创建SQLite数据库和5张表（含外键约束、唯一索引）
幂等设计（IF NOT EXISTS），可重复执行
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, DB_PATH


def init_database():
    os.makedirs(DATA_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 开启WAL模式（并发读写性能更好）
    cursor.execute("PRAGMA journal_mode=WAL;")
    # 开启外键约束
    cursor.execute("PRAGMA foreign_keys=ON;")

    # ===== 1. fund_info — 基金基本信息表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fund_info (
        fund_code       TEXT PRIMARY KEY,
        fund_name       TEXT NOT NULL,
        fund_company    TEXT,
        fund_type       TEXT,
        tracking_index  TEXT,
        risk_level      TEXT,
        fund_category   TEXT,
        top_holdings    TEXT,
        risk_points     TEXT,
        return_1y       TEXT,
        return_3y       TEXT,
        return_since_inception TEXT,
        inception_date  TEXT,
        created_at      TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # ===== 2. fund_holdings — 持仓管理表 =====
    # 定投信息已整合到本表（dca_* 字段）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fund_holdings (
        holding_id          INTEGER PRIMARY KEY,
        fund_code           TEXT NOT NULL,
        fund_name           TEXT,
        platform            TEXT NOT NULL,
        updated_at          TEXT,
        holding_shares      REAL DEFAULT 0,
        avg_buy_price       REAL DEFAULT 0,
        base_shares         REAL DEFAULT 0,
        current_price       REAL DEFAULT 0,
        holding_value       REAL DEFAULT 0,
        invested_capital    REAL DEFAULT 0,
        profit_loss_amount  REAL DEFAULT 0,
        return_rate         REAL DEFAULT 0,
        dca_is_active       INTEGER DEFAULT 0,
        dca_frequency       TEXT,
        dca_amount          REAL,
        dca_type            TEXT,
        dca_total_invested  REAL,
        first_buy_date      TEXT,
        last_update_date    TEXT,
        created_at          TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (fund_code) REFERENCES fund_info(fund_code)
    );
    """)

    # ===== 3. daily_quotes — 每日净值表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_quotes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_code       TEXT NOT NULL,
        date            TEXT NOT NULL,
        nav             REAL,
        acc_nav         REAL,
        daily_change_pct REAL,
        daily_value     REAL,
        daily_pnl       REAL,
        FOREIGN KEY (fund_code) REFERENCES fund_info(fund_code),
        UNIQUE(fund_code, date)
    );
    """)

    # ===== 4. trading_rules — 交易规则配置表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trading_rules (
        rule_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_category   TEXT NOT NULL,
        rule_type       TEXT NOT NULL,
        condition_desc  TEXT NOT NULL,
        threshold       REAL,
        action_desc     TEXT NOT NULL,
        priority        INTEGER DEFAULT 0,
        is_active       INTEGER DEFAULT 1,
        created_at      TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # ===== 5. trade_records — 交易记录表 =====
    # 合并了原 transactions（交易流水）和 trade_signals（交易信号）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_records (
        record_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_code           TEXT,
        fund_name           TEXT,
        record_type         TEXT,
        record_date         TEXT,
        signal_type         TEXT,
        trigger_condition   TEXT,
        trigger_value       REAL,
        suggested_action    TEXT,
        exec_status         TEXT DEFAULT '待执行',
        exec_date           TEXT,
        actual_action       TEXT,
        platform            TEXT,
        amount              REAL,
        shares              REAL,
        nav                 REAL,
        fee                 REAL DEFAULT 0,
        note                TEXT,
        created_at          TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # ===== 创建索引 =====
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_quotes_date ON daily_quotes(date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_quotes_fund ON daily_quotes(fund_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_rules_category ON trading_rules(fund_category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_rules_active ON trading_rules(is_active);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_date ON trade_records(record_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_fund ON trade_records(fund_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_status ON trade_records(exec_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_type ON trade_records(record_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_holdings_code ON fund_holdings(fund_code);")

    conn.commit()

    # 验证建表结果
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"数据库路径: {DB_PATH}")
    print(f"共 {len(tables)} 张表: {', '.join(tables)}")

    for table in tables:
        cursor.execute(f"PRAGMA table_info([{table}]);")
        cols = cursor.fetchall()
        cursor.execute(f"SELECT COUNT(*) FROM [{table}];")
        count = cursor.fetchone()[0]
        print(f"\n  [{table}] ({len(cols)} 列, {count} 条记录)")
        for col in cols:
            print(f"    {col[1]:25s} {col[2]:10s} {'PK' if col[5] else ''}")

    conn.close()
    print("\n数据库初始化完成!")


if __name__ == "__main__":
    init_database()
