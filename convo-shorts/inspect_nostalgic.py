import sqlite3, json

db_path = r'./data\nostalgic_db.sqlite'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check workflow_entity
cur.execute("SELECT COUNT(*) FROM workflow_entity")
wf_count = cur.fetchone()[0]
print(f'workflow_entity rows: {wf_count}')

if wf_count > 0:
    cur.execute("SELECT id, name, active, createdAt, updatedAt FROM workflow_entity")
    for row in cur.fetchall():
        print(f'  ID={row[0]}, Name={row[1]}, Active={row[2]}, Created={row[3]}, Updated={row[4]}')

# Also check credentials
cur.execute("SELECT COUNT(*) FROM credentials_entity")
cred_count = cur.fetchone()[0]
print(f'\ncredentials_entity rows: {cred_count}')

if cred_count > 0:
    cur.execute("SELECT id, name, type, createdAt FROM credentials_entity")
    for row in cur.fetchall():
        print(f'  ID={row[0]}, Name={row[1]}, Type={row[2]}, Created={row[3]}')

conn.close()
