import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
from backend.app.orchestration.supervisor import agentic_supervisor
from backend.app.schema.service import schema_service

catalog = schema_service.get_cached_catalog()

benchmarks = [
    ("Simple lookup", "What are our total orders?"),
    ("Data discovery", "Which tables contain customer information?"),
    ("Descriptive", "Show monthly revenue."),
    ("Diagnostic", "Why did revenue decline?"),
    ("Impact", "Is this decline statistically significant?"),
    ("Predictive", "Forecast revenue for the next three months."),
    ("Scenario", "What if prices increase by 5%?"),
    ("Prescriptive", "Which customer segments should management prioritize?"),
    ("Composite", "Explain the decline, forecast next quarter and recommend actions."),
]

print("=" * 80)
print("BENCHMARKING 9 QUESTION CATEGORIES ON AGENTIC SUPERVISOR")
print("=" * 80)

for cat_name, query in benchmarks:
    t0 = time.perf_counter()
    res = agentic_supervisor.supervise(question=query, catalog=catalog)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    print(f"\nCategory: [{cat_name}]")
    print(f"Query:    '{query}'")
    print(f"Success:  {res.success}")
    print(f"Latency:  {elapsed_ms:.1f}ms (Supervisor metric: {res.metrics.get('latency_ms', 0):.1f}ms)")
    print(f"Tasks:    {len(res.tasks)} tasks ({', '.join(t.task_type or t.specialist.value for t in res.tasks)})")
    if res.management_response:
        summary_preview = res.management_response.executive_summary[:90].replace('\n', ' ')
        print(f"Summary:  {summary_preview}...")
