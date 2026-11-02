import sqlite3
import json
from pathlib import Path

db_path = "ecommerce.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
tables = [r[0] for r in cur.fetchall()]

cur.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;")
views = [r[0] for r in cur.fetchall()]

cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
indexes = [r[0] for r in cur.fetchall()]

total_rows = 0
table_stats = {}
for t in tables:
    cur.execute(f'SELECT count(*) FROM "{t}";')
    cnt = cur.fetchone()[0]
    total_rows += cnt
    
    cur.execute(f'PRAGMA table_info("{t}");')
    cols = [c[1] for c in cur.fetchall()]
    
    cur.execute(f'PRAGMA foreign_key_list("{t}");')
    fks = cur.fetchall()
    
    table_stats[t] = {
        "rows": cnt,
        "column_count": len(cols),
        "columns": cols,
        "foreign_key_count": len(fks)
    }

conn.close()

print(f"Database: {db_path}")
print(f"Total Tables: {len(tables)}")
print(f"Total Views: {len(views)}")
print(f"Total Indexes: {len(indexes)}")
print(f"Total Rows: {total_rows:,}")
print("\nTop 10 Largest Tables:")
sorted_tables = sorted(table_stats.items(), key=lambda x: x[1]['rows'], reverse=True)
for t, s in sorted_tables[:10]:
    print(f"  {t:35} : {s['rows']:,} rows, {s['column_count']} cols, {s['foreign_key_count']} FKs")

with open("docs/ecommerce_db_inspection.json", "w", encoding="utf-8") as f:
    json.dump({
        "db_path": db_path,
        "table_count": len(tables),
        "view_count": len(views),
        "index_count": len(indexes),
        "total_rows": total_rows,
        "tables": table_stats
    }, f, indent=2)

print("\nSaved full schema to docs/ecommerce_db_inspection.json")
