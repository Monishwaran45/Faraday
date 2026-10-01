"""
run_benchmarks.py

Airtight, reproducible benchmark evaluation runner for Faraday.
Evaluates:
1. Real-World CVE Benchmark Corpus (experiments/datasets/real_world_cves.json)
2. Internal Safe-Code Regression Corpus (tests/test_security_regression.py)
3. OWASP, Juliet, and SARD SAST Profiles

Outputs:
- experiments/results/benchmark_summary.json
- Statistical precision, recall, F1, and FP/FN root cause distributions.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.core.file_scanner import CodeChunk
from backend.core.secret_scanner import scan_chunk
from backend.core.ast_analyzer import analyze_python_ast
from backend.models.model_backend import get_backend
from backend.core.dataset_benchmark import (
    evaluate_dataset,
    run_all_dataset_benchmarks,
    print_tool_comparison_table,
    BENCHMARK_PROFILES
)


def run_real_world_cve_benchmark() -> Dict[str, Any]:
    """Evaluates live detection against real-world CVE dataset."""
    cve_file = BASE_DIR / "experiments" / "datasets" / "real_world_cves.json"
    if not cve_file.exists():
        raise FileNotFoundError(f"Dataset file not found: {cve_file}")

    with open(cve_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    backend = get_backend()
    tp = 0
    fn = 0
    fp = 0
    tn = 0
    timings = []

    for item in cases:
        # 1. Test Vulnerable Code
        t0 = time.perf_counter()
        v_chunk = CodeChunk(
            file_path=f"vuln_{item['cve_id'].lower()}.{'js' if item['lang'] == 'javascript' else 'py'}",
            language=item["lang"],
            name="cve_vulnerable",
            start_line=1,
            end_line=len(item["vuln_code"].splitlines()),
            code=item["vuln_code"],
        )
        v_findings = scan_chunk(v_chunk)
        v_ai = backend.generate(f"Review code for vulnerabilities:\n{item['vuln_code']}")
        dt = (time.perf_counter() - t0) * 1000.0
        timings.append(dt)

        detected = (
            len(v_findings) > 0 or
            ("ISSUES:" in v_ai and "None found" not in v_ai)
        )
        if detected:
            tp += 1
        else:
            fn += 1

        # 2. Test Safe Patched Code
        t0 = time.perf_counter()
        s_chunk = CodeChunk(
            file_path=f"safe_{item['cve_id'].lower()}.{'js' if item['lang'] == 'javascript' else 'py'}",
            language=item["lang"],
            name="cve_safe",
            start_line=1,
            end_line=len(item["safe_code"].splitlines()),
            code=item["safe_code"],
        )
        s_findings = scan_chunk(s_chunk)
        s_ai = backend.generate(f"Review code for vulnerabilities:\n{item['safe_code']}")
        dt = (time.perf_counter() - t0) * 1000.0
        timings.append(dt)

        safe_clean = (
            len(s_findings) == 0 and
            ("None found" in s_ai or "ISSUES:" not in s_ai)
        )
        if safe_clean:
            tn += 1
        else:
            fp += 1

    total_samples = len(cases) * 2
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    avg_latency = sum(timings) / len(timings) if timings else 0.0

    return {
        "dataset": "real_world_cves",
        "name": "Real-World Historical Production CVE Corpus",
        "total_test_samples": total_samples,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "f1": round(f1 * 100, 1),
        "fpr": round(fpr * 100, 1),
        "avg_latency_ms": round(avg_latency, 2),
        "evaluated_cves": [c["cve_id"] for c in cases]
    }


def main():
    print("[*] Running Airtight Reproducible Faraday Benchmark Evaluation...")
    out_dir = BASE_DIR / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Real-World CVE Evaluation
    cve_results = run_real_world_cve_benchmark()
    print(f"  [+] Real-World CVEs: Precision={cve_results['precision']}%, Recall={cve_results['recall']}%, F1={cve_results['f1']}%")

    # 2. Industry-Standard SAST Profiles
    profile_results = {}
    for key in ["owasp", "juliet", "sard", "regression"]:
        profile_results[key] = evaluate_dataset(key)

    combined_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hardware_environment": {
            "platform": sys.platform,
            "python_version": sys.version.split()[0],
        },
        "real_world_cve_results": cve_results,
        "standard_benchmark_profiles": profile_results,
    }

    out_file = out_dir / "benchmark_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(combined_summary, f, indent=2)

    print(f"[+] Benchmark results persisted to: {out_file}")


if __name__ == "__main__":
    main()
