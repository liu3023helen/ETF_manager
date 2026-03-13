import sqlite3

conn = sqlite3.connect('data/etf_manager.db')
conn.row_factory = sqlite3.Row
tables = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    table_name = t['name']
    if table_name.startswith('sqlite_'): continue
    print(f'\n=== Table: {table_name} ===')
    print(t['sql'])
    
    print('Indexes:')
    for row in conn.execute(f"PRAGMA index_list({table_name})"):
        print(f"  Index: {row['name']} (unique: {row['unique']})")
        for col in conn.execute(f"PRAGMA index_info({row['name']})"):
            print(f"    Column: {col['name']}")
conn.close()
