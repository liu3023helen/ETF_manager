import sqlite3
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH

def migrate_database():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # 1. 备份旧数据（可选，这里为了简单直接删除重建，如需备份请先手动备份db文件）
        # print("Dropping old table daily_quotes...")
        conn.execute("DROP TABLE IF EXISTS daily_quotes")
        
        # 2. 创建新表
        print("Creating new table daily_quotes...")
        conn.execute("""
            CREATE TABLE daily_quotes (
                quote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_code TEXT NOT NULL,
                fund_name TEXT,
                quote_date TEXT NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                acc_nav REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(fund_code, quote_date)
            )
        """)
        
        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_fund_date ON daily_quotes(fund_code, quote_date)")
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
