"""
Database Reconnaissance Script for AI-Powered Data Scientist Agent
Inspects ecommerce.sqlite in strict read-only mode and outputs comprehensive schema,
row count, foreign key, index, and data quality profile.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path


def verify_readonly_connection(db_path: str):
    """Verifies that the database can be connected in read-only mode and writes are blocked."""
    uri_path = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri_path, uri=True)
    cursor = conn.cursor()

    # Test read
    cursor.execute("SELECT 1;")
    res = cursor.fetchone()
    if res[0] != 1:
        raise RuntimeError("Failed read check on database.")

    # Test write block
    write_blocked = False
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS __test_write_probe__ (id INT);")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "readonly" in str(e).lower() or "attempt to write a readonly database" in str(e).lower():
            write_blocked = True
        else:
            write_blocked = True
    except Exception:
        write_blocked = True

    if not write_blocked:
        raise RuntimeError("CRITICAL: Database was not opened in strict read-only mode! Write probe succeeded.")

    print(f"[SUCCESS] Verified strict read-only connection to: {db_path}")
    return conn


def inspect_database(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # 1. Get all tables and views
    cursor.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name;"
    )
    master_records = cursor.fetchall()

    tables = [r[1] for r in master_records if r[0] == 'table']
    views = [r[1] for r in master_records if r[0] == 'view']
    indexes_master = [r[1] for r in master_records if r[0] == 'index']

    print(f"Discovered: {len(tables)} tables, {len(views)} views, {len(indexes_master)} indexes in sqlite_master.")

    profile = {
        "tables_count": len(tables),
        "views_count": len(views),
        "indexes_count": len(indexes_master),
        "tables": {},
        "foreign_keys_graph": [],
        "total_rows": 0,
        "date_ranges": {},
    }

    for tbl in tables:
        # Row count
        cursor.execute(f'SELECT COUNT(*) FROM "{tbl}";')
        row_count = cursor.fetchone()[0]
        profile["total_rows"] += row_count

        # Table info (columns)
        cursor.execute(f'PRAGMA table_info("{tbl}");')
        columns_info = cursor.fetchall()
        # columns_info: cid, name, type, notnull, dflt_value, pk

        # Foreign keys
        cursor.execute(f'PRAGMA foreign_key_list("{tbl}");')
        fk_info = cursor.fetchall()
        # fk_info: id, seq, table, from, to, on_update, on_delete, match
        fks = []
        for fk in fk_info:
            fk_dict = {
                "id": fk[0],
                "seq": fk[1],
                "target_table": fk[2],
                "from_col": fk[3],
                "to_col": fk[4],
                "on_update": fk[5],
                "on_delete": fk[6],
                "match": fk[7]
            }
            fks.append(fk_dict)
            profile["foreign_keys_graph"].append({
                "source_table": tbl,
                "source_col": fk[3],
                "target_table": fk[2],
                "target_col": fk[4]
            })

        # Indexes
        cursor.execute(f'PRAGMA index_list("{tbl}");')
        idx_list = cursor.fetchall()
        # idx_list: seq, name, unique, origin, partial
        table_indexes = []
        for idx in idx_list:
            idx_name = idx[1]
            cursor.execute(f'PRAGMA index_info("{idx_name}");')
            idx_cols = [c[2] for c in cursor.fetchall()]
            table_indexes.append({
                "name": idx_name,
                "unique": bool(idx[2]),
                "origin": idx[3],
                "partial": bool(idx[4]),
                "columns": idx_cols
            })

        # Column profile: null count, distinct count, min/max
        col_profiles = []
        for col in columns_info:
            cid, col_name, col_type, notnull, dflt_value, pk = col
            
            # Profiling query
            try:
                cursor.execute(f'''
                    SELECT 
                        SUM(CASE WHEN "{col_name}" IS NULL THEN 1 ELSE 0 END) AS null_count,
                        COUNT(DISTINCT "{col_name}") AS distinct_count,
                        MIN("{col_name}") AS min_val,
                        MAX("{col_name}") AS max_val
                    FROM "{tbl}";
                ''')
                stats = cursor.fetchone()
                null_cnt = stats[0] if stats[0] is not None else 0
                dist_cnt = stats[1] if stats[1] is not None else 0
                min_v = stats[2]
                max_v = stats[3]
            except Exception as e:
                null_cnt = 0
                dist_cnt = 0
                min_v = None
                max_v = None

            # Detect potential date/timestamp column
            col_lower = col_name.lower()
            is_date = any(k in col_lower for k in ['date', 'time', 'timestamp', 'at', '_year', '_month', 'day'])
            if is_date and min_v is not None and max_v is not None:
                profile["date_ranges"][f"{tbl}.{col_name}"] = {
                    "min": str(min_v),
                    "max": str(max_v)
                }

            col_profiles.append({
                "cid": cid,
                "name": col_name,
                "type": col_type,
                "notnull": bool(notnull),
                "dflt_value": dflt_value,
                "pk": bool(pk),
                "null_count": null_cnt,
                "null_percentage": round((null_cnt / row_count * 100), 2) if row_count > 0 else 0.0,
                "distinct_count": dist_cnt,
                "min_sample": str(min_v)[:50] if min_v is not None else None,
                "max_sample": str(max_v)[:50] if max_v is not None else None,
            })

        profile["tables"][tbl] = {
            "row_count": row_count,
            "columns": col_profiles,
            "foreign_keys": fks,
            "indexes": table_indexes
        }
        print(f"  [Profiled] {tbl}: {row_count} rows, {len(col_profiles)} columns, {len(fks)} FKs, {len(table_indexes)} indexes")

    return profile


if __name__ == "__main__":
    db_file = "ecommerce.sqlite"
    if not os.path.exists(db_file):
        print(f"[ERROR] Database file not found at: {db_file}")
        sys.exit(1)

    conn = verify_readonly_connection(db_file)
    profile_data = inspect_database(conn)
    conn.close()

    os.makedirs("docs", exist_ok=True)
    with open("docs/dataset_profile_raw.json", "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2)

    print("\n[COMPLETE] Reconnaissance finished successfully. Profile JSON generated at docs/dataset_profile_raw.json")

