"""
Comprehensive End-to-End Latency Benchmark for 9 Business Analytical Question Categories.
Evaluates empirical p50, p95, p99, average latency, and success rates across all categories.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json
import time
import numpy as np
from typing import Dict, List, Any
from backend.app.orchestration.supervisor import agentic_supervisor
from backend.app.schema.service import schema_service

BENCHMARK_SUITE = [
    {
        "category": "Simple lookup",
        "question": "What are our total orders?",
        "description": "Direct metric aggregation and row count query",
    },
    {
        "category": "Data discovery",
        "question": "Which tables contain customer information?",
        "description": "Schema catalogue inspection and table metadata discovery",
    },
    {
        "category": "Descriptive",
        "question": "Show monthly revenue.",
        "description": "Multi-period temporal KPI aggregation and trend summary",
    },
    {
        "category": "Diagnostic",
        "question": "Why did revenue decline?",
        "description": "Driver variance decomposition and anomaly attribution",
    },
    {
        "category": "Impact",
        "question": "Is this decline statistically significant?",
        "description": "Hypothesis testing, Welch's t-test, Cohen's d effect size",
    },
    {
        "category": "Predictive",
        "question": "Forecast revenue for the next three months.",
        "description": "Multi-model tournament (ARIMA, Holt-Winters, Prophet, LightGBM)",
    },
    {
        "category": "Scenario",
        "question": "What if prices increase by 5%?",
        "description": "What-if simulation with demand elasticity shock curves",
    },
    {
        "category": "Prescriptive",
        "question": "Which customer segments should management prioritize?",
        "description": "Constrained mathematical optimization and churn risk prioritization",
    },
    {
        "category": "Composite",
        "question": "Explain the decline, forecast next quarter and recommend actions.",
        "description": "Multi-stage analytical pipeline: Diagnostic -> Predictive -> Prescriptive",
    },
]

def run_benchmarks(trials_per_category: int = 3) -> Dict[str, Any]:
    print("=" * 80)
    print(f"STARTING COMPREHENSIVE BENCHMARK RUN ({trials_per_category} trials per category)")
    print("Target LLM Provider: Groq Cloud API ONLY (openai/gpt-oss-120b)")
    print("=" * 80)

    catalog = schema_service.get_cached_catalog()
    results_by_category = []

    for item in BENCHMARK_SUITE:
        cat = item["category"]
        q = item["question"]
        print(f"\n---> Benchmarking Group: [{cat}]")
        print(f"     Prompt: '{q}'")

        durations_ms: List[float] = []
        successes = 0
        failures = 0
        abstentions = 0
        task_counts: List[int] = []

        for trial in range(1, trials_per_category + 1):
            t_start = time.perf_counter()
            exec_res = agentic_supervisor.supervise(
                question=q,
                catalog=catalog,
                session_id=f"bench_{cat.lower().replace(' ', '_')}_{trial}",
            )
            t_end = time.perf_counter()
            duration = (t_end - t_start) * 1000
            durations_ms.append(duration)
            task_counts.append(len(exec_res.tasks))

            if exec_res.success:
                successes += 1
            elif exec_res.abstain_reason:
                abstentions += 1
            else:
                failures += 1

            print(f"     Trial {trial}/{trials_per_category}: {duration:.1f}ms | success={exec_res.success} | tasks={len(exec_res.tasks)}")

        p50 = float(np.percentile(durations_ms, 50))
        p95 = float(np.percentile(durations_ms, 95))
        p99 = float(np.percentile(durations_ms, 99))
        avg = float(np.mean(durations_ms))
        min_lat = float(np.min(durations_ms))
        max_lat = float(np.max(durations_ms))
        success_rate = (successes / trials_per_category) * 100.0

        group_summary = {
            "category": cat,
            "question": q,
            "trials": trials_per_category,
            "success_rate_pct": round(success_rate, 1),
            "success_count": successes,
            "failure_count": failures,
            "abstention_count": abstentions,
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "p99_ms": round(p99, 1),
            "avg_ms": round(avg, 1),
            "min_ms": round(min_lat, 1),
            "max_ms": round(max_lat, 1),
            "avg_tasks": round(float(np.mean(task_counts)), 1),
        }
        results_by_category.append(group_summary)

    # Print summary table
    print("\n" + "=" * 100)
    print(f"{'Category':<16} | {'Reqs':<5} | {'Success%':<8} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'Avg (ms)':<9} | {'Min (ms)':<9} | {'Max (ms)':<9}")
    print("-" * 100)
    for r in results_by_category:
        print(f"{r['category']:<16} | {r['trials']:<5} | {r['success_rate_pct']:<7}% | {r['p50_ms']:<9.1f} | {r['p95_ms']:<9.1f} | {r['avg_ms']:<9.1f} | {r['min_ms']:<9.1f} | {r['max_ms']:<9.1f}")
    print("=" * 100)

    # Save to JSON
    os.makedirs("backend/data", exist_ok=True)
    out_file = "backend/data/benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results_by_category, f, indent=2)
    print(f"\nDetailed benchmark results persisted to: {out_file}")

    return {"results": results_by_category}

if __name__ == "__main__":
    run_benchmarks(trials_per_category=3)
