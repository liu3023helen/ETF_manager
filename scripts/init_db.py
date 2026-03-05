"""
ETF管理系统 - 数据库初始化脚本
创建SQLite数据库和7张表（含外键约束、唯一索引）
幂等设计（IF NOT EXISTS），可重复执行
"""

import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "etf_manager.db")


def init_database():
    os.makedirs(DB_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 开启WAL模式（并发读写性能更好）
    cursor.execute("PRAGMA journal_mode=WAL;")
    # 开启外键约束
    cursor.execute("PRAGMA foreign_keys=ON;")

    # ===== 1. 基金基本信息表（只增不减） =====
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
        created_at      TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # ===== 2. 持仓管理表 =====
    # holding_id 不使用 AUTOINCREMENT，由应用层维护连续编号
    # 一个基金在一个平台只有一条记录（实时持仓）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS my_holdings (
        holding_id      INTEGER PRIMARY KEY,
        fund_code       TEXT NOT NULL,
        platform        TEXT NOT NULL,
        shares          REAL DEFAULT 0,
        cost_price      REAL DEFAULT 0,
        base_shares     REAL DEFAULT 0,
        tradable_shares REAL DEFAULT 0,
        current_value   REAL DEFAULT 0,
        total_invested  REAL DEFAULT 0,
        latest_nav      REAL DEFAULT 0,
        nav_date        TEXT,
        first_buy_date  TEXT,
        updated_at      TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (fund_code) REFERENCES fund_info(fund_code),
        UNIQUE(fund_code, platform)
    );
    """)

    # ===== 3. 每日净值表（历史数据，一基金多天） =====
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

    # ===== 4. 定投计划表（只增不减） =====
    # 修改计划 = 旧行end_date改为当天 + 新行插入
    # 当前生效计划：end_date = '9999-12-31' AND is_active = 1
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dca_plans (
        plan_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_code       TEXT NOT NULL,
        platform        TEXT,
        is_active       INTEGER DEFAULT 1,
        frequency       TEXT,
        amount          REAL,
        dca_type        TEXT DEFAULT '固定金额',
        total_invested  REAL DEFAULT 0,
        start_date      TEXT,
        end_date        TEXT DEFAULT '9999-12-31',
        FOREIGN KEY (fund_code) REFERENCES fund_info(fund_code)
    );
    """)

    # ===== 5. 交易记录表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_code       TEXT NOT NULL,
        platform        TEXT,
        tx_type         TEXT NOT NULL,
        tx_date         TEXT NOT NULL,
        amount          REAL,
        shares          REAL,
        nav_at_tx       REAL,
        fee             REAL DEFAULT 0,
        note            TEXT,
        FOREIGN KEY (fund_code) REFERENCES fund_info(fund_code)
    );
    """)

    # ===== 6. 交易规则配置表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trading_rules (
        rule_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_category   TEXT NOT NULL,
        rule_type       TEXT NOT NULL,
        condition_desc  TEXT NOT NULL,
        threshold       REAL,
        action_desc     TEXT NOT NULL,
        priority        INTEGER DEFAULT 0,
        is_active       INTEGER DEFAULT 1
    );
    """)

    # ===== 7. 交易信号表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_signals (
        signal_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_code       TEXT NOT NULL,
        signal_date     TEXT NOT NULL,
        signal_type     TEXT NOT NULL,
        trigger_condition TEXT,
        suggested_action TEXT,
        exec_status     TEXT DEFAULT '待执行',
        actual_action   TEXT,
        created_at      TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (fund_code) REFERENCES fund_info(fund_code)
    );
    """)

    # ===== 创建索引 =====
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_quotes_date ON daily_quotes(date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_quotes_fund ON daily_quotes(fund_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(tx_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_fund ON transactions(fund_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_signals_date ON trade_signals(signal_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_signals_fund ON trade_signals(fund_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_signals_status ON trade_signals(exec_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dca_plans_active ON dca_plans(end_date, is_active);")

    conn.commit()

    # 验证建表结果
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"数据库已创建: {DB_PATH}")
    print(f"共 {len(tables)} 张表: {', '.join(tables)}")

    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        cols = cursor.fetchall()
        print(f"\n  [{table}] ({len(cols)} 列)")
        for col in cols:
            print(f"    {col[1]:25s} {col[2]:10s} {'PK' if col[5] else ''}")

    conn.close()
    print("\n数据库初始化完成!")


if __name__ == "__main__":
    init_database()
