import sqlite3
import numpy as np

conn = sqlite3.connect('agent_app.sqlite')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('SELECT COUNT(*) as cnt FROM ops_run_traces')
total = cur.fetchone()['cnt']
print(f'Total traces in DB: {total}')

cur.execute('''
    SELECT run_id, query, intent, latency_ms, verification_status, error_class, created_at, sql_executed, row_count
    FROM ops_run_traces 
    ORDER BY latency_ms DESC 
    LIMIT 40
''')
slowest = cur.fetchall()
print('\nTop 40 Slowest Traces:')
for r in slowest:
    q = r['query'][:60].replace('\n', ' ') if r['query'] else ''
    sql = r['sql_executed'][:50].replace('\n', ' ') if r['sql_executed'] else 'None'
    print(f"{r['run_id']} | {r['latency_ms']:.1f}ms ({r['latency_ms']/1000:.2f}s) | status={r['verification_status']} | err={r['error_class']} | intent={r['intent']} | query={q} | sql={sql} | created={r['created_at']}")

cur.execute('SELECT latency_ms FROM ops_run_traces')
all_lats = [r['latency_ms'] for r in cur.fetchall()]
if all_lats:
    print(f"\nLatency Distribution ({len(all_lats)} samples):")
    print(f"min:  {np.min(all_lats):.1f} ms")
    print(f"p25:  {np.percentile(all_lats, 25):.1f} ms")
    print(f"p50:  {np.percentile(all_lats, 50):.1f} ms")
    print(f"p75:  {np.percentile(all_lats, 75):.1f} ms")
    print(f"p90:  {np.percentile(all_lats, 90):.1f} ms")
    print(f"p95:  {np.percentile(all_lats, 95):.1f} ms")
    print(f"p99:  {np.percentile(all_lats, 99):.1f} ms")
    print(f"max:  {np.max(all_lats):.1f} ms")
    print(f"mean: {np.mean(all_lats):.1f} ms")

# Distribution by error_class and verification_status
print("\nBreakdown by verification_status and error_class:")
cur.execute('''
    SELECT verification_status, error_class, COUNT(*) as cnt, AVG(latency_ms) as avg_lat, MIN(latency_ms) as min_lat, MAX(latency_ms) as max_lat
    FROM ops_run_traces
    GROUP BY verification_status, error_class
    ORDER BY cnt DESC
''')
for r in cur.fetchall():
    print(f"status={r['verification_status']:<15} | err={str(r['error_class']):<25} | cnt={r['cnt']:<5} | avg={r['avg_lat']:.1f}ms | min={r['min_lat']:.1f}ms | max={r['max_lat']:.1f}ms")

# Check where the latencies > 10,000ms come from
cur.execute('''
    SELECT verification_status, error_class, intent, COUNT(*) as cnt, AVG(latency_ms) as avg_lat
    FROM ops_run_traces
    WHERE latency_ms > 10000
    GROUP BY verification_status, error_class, intent
    ORDER BY cnt DESC
''')
print("\nBreakdown of traces with latency > 10s:")
for r in cur.fetchall():
    print(f"status={r['verification_status']:<15} | err={str(r['error_class']):<25} | intent={r['intent']:<15} | cnt={r['cnt']:<5} | avg={r['avg_lat']:.1f}ms")

conn.close()

print("\n" + "="*50)
print("SOURCE BREAKDOWN: AgenticSupervisor vs MultiAgentOrchestrator")
print("="*50)
conn = sqlite3.connect('agent_app.sqlite')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) as cnt FROM ops_run_traces WHERE run_id LIKE 'exec_%'")
exec_cnt = cur.fetchone()['cnt']
cur.execute("SELECT COUNT(*) as cnt FROM ops_run_traces WHERE run_id NOT LIKE 'exec_%'")
non_exec_cnt = cur.fetchone()['cnt']
print(f"Traces from AgenticSupervisor (exec_*): {exec_cnt}")
print(f"Traces from MultiAgentOrchestrator (UUID): {non_exec_cnt}")

cur.execute("SELECT AVG(latency_ms), MIN(latency_ms), MAX(latency_ms) FROM ops_run_traces WHERE run_id LIKE 'exec_%'")
row = cur.fetchone()
if row and row[0] is not None:
    print(f"Supervisor (exec_*): avg={row[0]:.1f}ms, min={row[1]:.1f}ms, max={row[2]:.1f}ms")

cur.execute("SELECT AVG(latency_ms), MIN(latency_ms), MAX(latency_ms) FROM ops_run_traces WHERE run_id NOT LIKE 'exec_%'")
row = cur.fetchone()
if row and row[0] is not None:
    print(f"MultiAgentOrchestrator: avg={row[0]:.1f}ms, min={row[1]:.1f}ms, max={row[2]:.1f}ms")

cur.execute("SELECT COUNT(*) as cnt FROM ops_run_traces WHERE run_id LIKE 'exec_%' AND latency_ms > 10000")
print(f"Supervisor > 10s: {cur.fetchone()['cnt']}")
cur.execute("SELECT COUNT(*) as cnt FROM ops_run_traces WHERE run_id NOT LIKE 'exec_%' AND latency_ms > 10000")
print(f"MultiAgentOrchestrator > 10s: {cur.fetchone()['cnt']}")

cur.execute("SELECT latency_ms FROM ops_run_traces WHERE run_id LIKE 'exec_%'")
sup_lats = [r['latency_ms'] for r in cur.fetchall()]
if sup_lats:
    print(f"\nAgenticSupervisor latency percentiles ({len(sup_lats)} samples):")
    print(f"p50: {np.percentile(sup_lats, 50):.1f}ms")
    print(f"p95: {np.percentile(sup_lats, 95):.1f}ms")
    print(f"p99: {np.percentile(sup_lats, 99):.1f}ms")
    print(f"max: {np.max(sup_lats):.1f}ms")

cur.execute("SELECT latency_ms FROM ops_run_traces WHERE run_id NOT LIKE 'exec_%'")
multi_lats = [r['latency_ms'] for r in cur.fetchall()]
if multi_lats:
    print(f"\nMultiAgentOrchestrator latency percentiles ({len(multi_lats)} samples):")
    print(f"p50: {np.percentile(multi_lats, 50):.1f}ms")
    print(f"p95: {np.percentile(multi_lats, 95):.1f}ms")
    print(f"p99: {np.percentile(multi_lats, 99):.1f}ms")
    print(f"max: {np.max(multi_lats):.1f}ms")

conn.close()
