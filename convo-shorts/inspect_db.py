import sqlite3, json

db_path = r'C:\Users\saini\n8n-yt-automation\data-recovered\database.sqlite'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('ALL TABLES:')
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    count = cur.fetchone()[0]
    print(f'  {t}: {count} rows')

print()

# Find workflow data
for t in tables:
    if 'workflow' in t.lower():
        print(f'\n=== {t} ===')
        cur.execute(f'SELECT * FROM "{t}" LIMIT 5')
        rows = cur.fetchall()
        cur.execute(f'PRAGMA table_info("{t}")')
        cols = [c[1] for c in cur.fetchall()]
        print('Columns:', cols)
        for row in rows:
            print(dict(zip(cols, row)))

conn.close()
