import sqlite3

DB_PATH = r"e:\LXY_learn\ETF_manager\data\etf_manager.db"

TABLES_TO_DROP = [
    "transactions",
    "trade_signals",
    "daily_quotes",
    "dca_plans",
]


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for table in TABLES_TO_DROP:
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"已删除表: {table} (如果存在的话)")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
