"""
ETF Manager v3 - Database Migration Script
===========================================
Changes:
1. fund_holdings: ADD COLUMN total_sold (REAL DEFAULT 0)
2. fund_holdings: ADD COLUMN net_invested (REAL DEFAULT 0)
3. fund_holdings: ADD UNIQUE(fund_code, platform) constraint
4. Backfill total_sold / net_invested from trade_records replay
5. Rebuild all fund_holdings via full trade replay
6. Validate results

Run: python scripts/migrate_db_v3.py
"""

import sqlite3
import shutil
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


def backup_database(db_path):
    """Create a timestamped backup before migration."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path + f".backup_v3_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"[BACKUP] {backup_path}")
    return backup_path


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info([{table}]);")
    return any(row[1] == column for row in cursor.fetchall())


def index_exists(cursor, index_name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?;", (index_name,))
    return cursor.fetchone() is not None


def step1_add_columns(cursor):
    """Add total_sold and net_invested columns to fund_holdings."""
    print("\n[STEP 1] Adding new columns to fund_holdings...")

    if not column_exists(cursor, "fund_holdings", "total_sold"):
        cursor.execute("ALTER TABLE fund_holdings ADD COLUMN total_sold REAL DEFAULT 0;")
        print("  + Added column: total_sold")
    else:
        print("  - total_sold already exists, skipping")

    if not column_exists(cursor, "fund_holdings", "net_invested"):
        cursor.execute("ALTER TABLE fund_holdings ADD COLUMN net_invested REAL DEFAULT 0;")
        print("  + Added column: net_invested")
    else:
        print("  - net_invested already exists, skipping")


def step2_add_unique_constraint(cursor):
    """Add UNIQUE(fund_code, platform) to fund_holdings.
    
    SQLite does not support ADD CONSTRAINT, so we create a unique index instead.
    """
    print("\n[STEP 2] Adding UNIQUE(fund_code, platform) constraint...")

    if not index_exists(cursor, "uq_holdings_fund_platform"):
        # First check for duplicates
        cursor.execute("""
            SELECT fund_code, platform, COUNT(*) as cnt
            FROM fund_holdings
            GROUP BY fund_code, platform
            HAVING cnt > 1;
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            print("  ! Found duplicates - merging before adding constraint:")
            for row in duplicates:
                print(f"    {row[0]} @ {row[1]}: {row[2]} records")
                # Keep the one with the latest updated_at, delete others
                cursor.execute("""
                    DELETE FROM fund_holdings
                    WHERE rowid NOT IN (
                        SELECT MIN(rowid) FROM fund_holdings
                        GROUP BY fund_code, platform
                    );
                """)
                print(f"    Merged duplicates, kept earliest rowid for each group")

        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_holdings_fund_platform "
            "ON fund_holdings(fund_code, platform);"
        )
        print("  + Created unique index: uq_holdings_fund_platform")
    else:
        print("  - Unique index already exists, skipping")


def replay_trades_for_holding(cursor, fund_code, platform):
    """Replay all executed trades for a (fund_code, platform) pair.
    
    Returns a dict with recalculated holding fields.
    """
    cursor.execute("""
        SELECT record_type, amount, shares, nav, fee, record_date
        FROM trade_records
        WHERE fund_code = ?
          AND platform = ?
          AND exec_status = '已执行'
          AND record_type IN ('买入', '卖出', '定投')
        ORDER BY record_date ASC, record_id ASC;
    """, (fund_code, platform))
    trades = cursor.fetchall()

    holding_shares = 0.0
    avg_buy_price = 0.0
    invested_capital = 0.0
    total_sold = 0.0
    first_buy_date = None

    for trade in trades:
        record_type, amount, shares, nav, fee, record_date = trade
        amount = amount or 0
        shares = shares or 0
        nav = nav or 0
        fee = fee or 0

        if record_type in ('买入', '定投'):
            if shares <= 0:
                continue

            # Effective NAV for cost calculation
            effective_nav = nav if nav > 0 else (amount / shares if amount > 0 else 0)
            
            # Weighted average cost
            old_shares = holding_shares
            old_cost = avg_buy_price
            new_shares = round(old_shares + shares, 2)
            
            nav_for_cost = effective_nav if effective_nav > 0 else old_cost
            if new_shares > 0:
                avg_buy_price = round(
                    (old_shares * old_cost + shares * nav_for_cost) / new_shares, 4
                )
            
            holding_shares = new_shares
            tx_amount = round(amount, 2) if amount > 0 else round(shares * nav_for_cost, 2)
            invested_capital = round(invested_capital + tx_amount, 2)

            if first_buy_date is None:
                first_buy_date = record_date

        elif record_type == '卖出':
            if shares <= 0 or holding_shares <= 0:
                continue

            sell_shares = min(shares, holding_shares)
            holding_shares = round(holding_shares - sell_shares, 2)
            
            # Calculate sold amount
            sell_nav = nav if nav > 0 else avg_buy_price
            sell_amount = round(amount, 2) if amount > 0 else round(sell_shares * sell_nav, 2)
            total_sold = round(total_sold + sell_amount, 2)

    net_invested = round(invested_capital - total_sold, 2)
    base_shares = round(holding_shares * 0.2, 2)

    return {
        'holding_shares': holding_shares,
        'avg_buy_price': avg_buy_price,
        'base_shares': base_shares,
        'invested_capital': invested_capital,
        'total_sold': total_sold,
        'net_invested': net_invested,
        'first_buy_date': first_buy_date,
    }


def step3_rebuild_holdings(cursor):
    """Rebuild all fund_holdings by replaying trade_records."""
    print("\n[STEP 3] Rebuilding all fund_holdings via trade replay...")

    # Get all existing holdings
    cursor.execute("SELECT holding_id, fund_code, platform FROM fund_holdings;")
    holdings = cursor.fetchall()
    print(f"  Found {len(holdings)} holdings to rebuild")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rebuilt = 0

    for holding_id, fund_code, platform in holdings:
        result = replay_trades_for_holding(cursor, fund_code, platform)

        cursor.execute("""
            UPDATE fund_holdings
            SET holding_shares = ?,
                avg_buy_price = ?,
                base_shares = ?,
                invested_capital = ?,
                total_sold = ?,
                net_invested = ?,
                first_buy_date = COALESCE(?, first_buy_date),
                updated_at = ?
            WHERE holding_id = ?;
        """, (
            result['holding_shares'],
            result['avg_buy_price'],
            result['base_shares'],
            result['invested_capital'],
            result['total_sold'],
            result['net_invested'],
            result['first_buy_date'],
            now,
            holding_id,
        ))
        rebuilt += 1
        print(f"  [{rebuilt}/{len(holdings)}] {fund_code} @ {platform}: "
              f"shares={result['holding_shares']}, "
              f"invested={result['invested_capital']}, "
              f"sold={result['total_sold']}, "
              f"net={result['net_invested']}")

    print(f"  Rebuilt {rebuilt} holdings")


def step4_validate(cursor):
    """Validate migration results."""
    print("\n[STEP 4] Validating results...")
    errors = []

    # Check all holdings have total_sold and net_invested
    cursor.execute("""
        SELECT holding_id, fund_code, platform,
               invested_capital, total_sold, net_invested
        FROM fund_holdings;
    """)
    holdings = cursor.fetchall()

    for h_id, fund_code, platform, invested, sold, net in holdings:
        invested = invested or 0
        sold = sold or 0
        net = net or 0

        # net_invested should equal invested_capital - total_sold
        expected_net = round(invested - sold, 2)
        if abs(net - expected_net) > 0.01:
            errors.append(
                f"  holding_id={h_id} ({fund_code}@{platform}): "
                f"net_invested={net} != invested-sold={expected_net}"
            )

        # total_sold should be non-negative
        if sold < 0:
            errors.append(
                f"  holding_id={h_id} ({fund_code}@{platform}): "
                f"total_sold={sold} is negative"
            )

    # Verify no duplicate (fund_code, platform)
    cursor.execute("""
        SELECT fund_code, platform, COUNT(*)
        FROM fund_holdings
        GROUP BY fund_code, platform
        HAVING COUNT(*) > 1;
    """)
    dups = cursor.fetchall()
    if dups:
        for d in dups:
            errors.append(f"  Duplicate: {d[0]}@{d[1]} ({d[2]} records)")

    # Verify unique index exists
    if not index_exists(cursor, "uq_holdings_fund_platform"):
        errors.append("  Missing unique index: uq_holdings_fund_platform")

    if errors:
        print("  VALIDATION FAILED:")
        for e in errors:
            print(f"    {e}")
        return False
    else:
        print(f"  Validated {len(holdings)} holdings - ALL OK")
        return True


def main():
    print("=" * 60)
    print("ETF Manager - Database Migration v3")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    print(f"Database: {DB_PATH}")

    # Backup
    backup_path = backup_database(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")

    try:
        step1_add_columns(cursor)
        step2_add_unique_constraint(cursor)
        step3_rebuild_holdings(cursor)

        valid = step4_validate(cursor)
        if valid:
            conn.commit()
            print("\n[SUCCESS] Migration completed and committed!")
        else:
            conn.rollback()
            print("\n[ROLLBACK] Validation failed, changes rolled back.")
            print(f"Backup at: {backup_path}")
            sys.exit(1)

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        print(f"Backup at: {backup_path}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

    # Post-migration summary
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fund_code, platform, holding_shares,
               invested_capital, total_sold, net_invested
        FROM fund_holdings
        ORDER BY fund_code, platform;
    """)
    rows = cursor.fetchall()
    print(f"\n{'='*60}")
    print("Post-migration fund_holdings summary:")
    print(f"{'Fund':<10} {'Platform':<8} {'Shares':>10} {'Invested':>10} {'Sold':>10} {'Net':>10}")
    print("-" * 60)
    for row in rows:
        print(f"{row[0]:<10} {row[1] or '':<8} {row[2] or 0:>10.2f} "
              f"{row[3] or 0:>10.2f} {row[4] or 0:>10.2f} {row[5] or 0:>10.2f}")
    conn.close()


if __name__ == "__main__":
    main()
