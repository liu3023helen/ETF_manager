import sqlite3
import os

DB_PATH = "data/etf_manager.db"

def migrate():
    print("Starting database migration...")
    
    # Enable foreign keys in sqlite
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    
    # Read the current data
    print("Reading old data...")
    fund_holdings_old = conn.execute("SELECT * FROM fund_holdings").fetchall()
    trade_records_old = conn.execute("SELECT * FROM trade_records").fetchall()
    daily_quotes_old = conn.execute("SELECT * FROM daily_quotes").fetchall()
    
    # Create new tables
    print("Creating new tables...")
    
    conn.execute("DROP TABLE IF EXISTS fund_holdings_new")
    conn.execute("""
        CREATE TABLE fund_holdings_new (
            holding_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            platform TEXT,
            holding_shares REAL,
            avg_buy_price REAL,
            base_shares REAL,
            current_price REAL,
            holding_value REAL,
            invested_capital REAL,
            profit_loss_amount REAL,
            return_rate REAL,
            dca_is_active INTEGER,
            dca_frequency TEXT,
            dca_amount REAL,
            dca_type TEXT,
            dca_total_invested REAL,
            first_buy_date TEXT,
            last_update_date TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(fund_code) REFERENCES fund_info(fund_code)
        )
    """)
    
    conn.execute("DROP TABLE IF EXISTS trade_records_new")
    conn.execute("""
        CREATE TABLE trade_records_new (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            record_type TEXT,
            record_date TEXT,
            signal_type TEXT,
            trigger_condition TEXT,
            trigger_value REAL,
            suggested_action TEXT,
            exec_status TEXT DEFAULT '待执行',
            exec_date TEXT,
            actual_action TEXT,
            platform TEXT,
            amount REAL,
            shares REAL,
            nav REAL,
            fee REAL DEFAULT 0,
            note TEXT,
            created_at TEXT,
            FOREIGN KEY(fund_code) REFERENCES fund_info(fund_code)
        )
    """)
    
    conn.execute("DROP TABLE IF EXISTS daily_quotes_new")
    conn.execute("""
        CREATE TABLE daily_quotes_new (
            quote_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            quote_date TEXT NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            acc_nav REAL,
            created_at TEXT,
            UNIQUE(fund_code, quote_date),
            FOREIGN KEY(fund_code) REFERENCES fund_info(fund_code)
        )
    """)
    
    # Insert old data into new tables, ignoring fund_name
    print(f"Migrating {len(fund_holdings_old)} fund_holdings...")
    for row in fund_holdings_old:
        r = dict(row)
        conn.execute("""
            INSERT INTO fund_holdings_new (
                holding_id, fund_code, platform, holding_shares, avg_buy_price, 
                base_shares, current_price, holding_value, invested_capital, 
                profit_loss_amount, return_rate, dca_is_active, dca_frequency, 
                dca_amount, dca_type, dca_total_invested, first_buy_date, 
                last_update_date, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r['holding_id'], r['fund_code'], r.get('platform'), r.get('holding_shares'), r.get('avg_buy_price'),
            r.get('base_shares'), r.get('current_price'), r.get('holding_value'), r.get('invested_capital'),
            r.get('profit_loss_amount'), r.get('return_rate'), r.get('dca_is_active'), r.get('dca_frequency'),
            r.get('dca_amount'), r.get('dca_type'), r.get('dca_total_invested'), r.get('first_buy_date'),
            r.get('last_update_date'), r.get('created_at'), r.get('updated_at')
        ))

    print(f"Migrating {len(trade_records_old)} trade_records...")
    for row in trade_records_old:
        r = dict(row)
        conn.execute("""
            INSERT INTO trade_records_new (
                record_id, fund_code, record_type, record_date, signal_type,
                trigger_condition, trigger_value, suggested_action, exec_status,
                exec_date, actual_action, platform, amount, shares, nav, fee, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r['record_id'], r['fund_code'], r.get('record_type'), r.get('record_date'), r.get('signal_type'),
            r.get('trigger_condition'), r.get('trigger_value'), r.get('suggested_action'), r.get('exec_status'),
            r.get('exec_date'), r.get('actual_action'), r.get('platform'), r.get('amount'), r.get('shares'),
            r.get('nav'), r.get('fee'), r.get('note'), r.get('created_at')
        ))

    print(f"Migrating {len(daily_quotes_old)} daily_quotes...")
    for row in daily_quotes_old:
        r = dict(row)
        conn.execute("""
            INSERT INTO daily_quotes_new (
                quote_id, fund_code, quote_date, open_price, high_price,
                low_price, close_price, acc_nav, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r['quote_id'], r['fund_code'], r.get('quote_date'), r.get('open_price'), r.get('high_price'),
            r.get('low_price'), r.get('close_price'), r.get('acc_nav'), r.get('created_at')
        ))
        
    print("Dropping old tables...")
    conn.execute("DROP TABLE fund_holdings")
    conn.execute("DROP TABLE trade_records")
    conn.execute("DROP TABLE daily_quotes")
    
    print("Renaming new tables to original names...")
    conn.execute("ALTER TABLE fund_holdings_new RENAME TO fund_holdings")
    conn.execute("ALTER TABLE trade_records_new RENAME TO trade_records")
    conn.execute("ALTER TABLE daily_quotes_new RENAME TO daily_quotes")
    
    # Re-create indexes
    print("Re-creating indexes...")
    conn.execute("CREATE INDEX idx_fund_holdings_code ON fund_holdings(fund_code)")
    conn.execute("CREATE INDEX idx_trade_records_type ON trade_records(record_type)")
    conn.execute("CREATE INDEX idx_trade_records_status ON trade_records(exec_status)")
    conn.execute("CREATE INDEX idx_trade_records_fund ON trade_records(fund_code)")
    conn.execute("CREATE INDEX idx_trade_records_date ON trade_records(record_date)")
    conn.execute("CREATE INDEX idx_quotes_fund_date ON daily_quotes(fund_code, quote_date)")
    
    conn.commit()
    conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
