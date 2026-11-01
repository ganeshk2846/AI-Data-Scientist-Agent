"""
Audit script to check:
1. Foreign key integrity across all tables
2. Primary key presence and uniqueness
3. High null percentages across columns
4. Distribution / range checks on key metric fields
5. Candidate relationships / entity joining paths
"""

import sqlite3
import json

conn = sqlite3.connect("file:ecommerce.sqlite?mode=ro", uri=True)
cur = conn.cursor()

print("--- 1. Foreign Key Violations Check ---")
cur.execute("PRAGMA foreign_key_check;")
fk_violations = cur.fetchall()
print(f"Total FK violations: {len(fk_violations)}")
if fk_violations:
    for v in fk_violations[:10]:
        print(f"  Violation in table '{v[0]}', rowid {v[1]}, target '{v[2]}', fkid {v[3]}")

print("\n--- 2. Primary Key Analysis ---")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
tables = [r[0] for r in cur.fetchall()]

tables_without_pk = []
for t in tables:
    cur.execute(f'PRAGMA table_info("{t}");')
    cols = cur.fetchall()
    pks = [c[1] for c in cols if c[5] > 0]
    if not pks:
        tables_without_pk.append(t)
    else:
        pk_cols = ", ".join(f'"{p}"' for p in pks)
        cur.execute(f'SELECT COUNT(*) FROM (SELECT {pk_cols} FROM "{t}" GROUP BY {pk_cols} HAVING COUNT(*) > 1);')
        dupes = cur.fetchone()[0]
        if dupes > 0:
            print(f"  [WARNING] Table '{t}' has {dupes} duplicate PK records!")

print(f"Tables without explicit Primary Key ({len(tables_without_pk)}): {tables_without_pk}")

print("\n--- 3. High Null Rate Columns (> 20%) ---")
for t in tables:
    cur.execute(f'PRAGMA table_info("{t}");')
    cols = [c[1] for c in cur.fetchall()]
    cur.execute(f'SELECT COUNT(*) FROM "{t}";')
    total = cur.fetchone()[0]
    if total == 0:
        continue
    for c in cols:
        cur.execute(f'SELECT COUNT(*) FROM "{t}" WHERE "{c}" IS NULL;')
        nulls = cur.fetchone()[0]
        pct = (nulls / total) * 100
        if pct > 20:
            print(f"  {t}.{c}: {nulls}/{total} NULL ({pct:.1f}%)")

print("\n--- 4. Order and Revenue Sanity Check ---")
cur.execute("""
    SELECT 
        COUNT(*) as order_count,
        MIN(total_amount),
        MAX(total_amount),
        AVG(total_amount),
        SUM(total_amount)
    FROM orders;
""")
o_stats = cur.fetchone()
print(f"Orders: Count={o_stats[0]}, Min={o_stats[1]}, Max={o_stats[2]}, Avg={o_stats[3]:.2f}, Total={o_stats[4]:.2f}")

cur.execute("""
    SELECT order_status, COUNT(*), SUM(total_amount) 
    FROM orders 
    GROUP BY order_status 
    ORDER BY COUNT(*) DESC;
""")
print("Orders by status:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} orders, sum={r[2]:.2f}")

cur.execute("""
    SELECT payment_status, COUNT(*), SUM(amount) 
    FROM payments 
    GROUP BY payment_status 
    ORDER BY COUNT(*) DESC;
""")
print("\nPayments by status:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} payments, sum={r[2]:.2f}")

cur.execute("""
    SELECT MIN(order_date), MAX(order_date) FROM orders;
""")
print(f"\nOrder Date Span: {cur.fetchone()}")

conn.close()
