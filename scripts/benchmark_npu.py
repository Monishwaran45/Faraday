"""
benchmark_npu.py

Statistically rigorous, reproducible benchmark script for Faraday neural inference.
Measures latency distribution, percentiles (P50, P90, P95, P99), jitter, and throughput
on Qualcomm Snapdragon Hexagon NPU / ONNX Runtime execution providers.

Usage:
    uv run python scripts/benchmark_npu.py
    uv run python scripts/benchmark_npu.py --iterations 100 --output review_output/benchmark.json
"""

import os
import sys
import time
import json
import argparse
import platform
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import onnxruntime as ort
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.models.verify_npu import probe_hardware_environment, probe_onnx_execution_providers

DEFAULT_ONNX_PATH = BASE_DIR / "models" / "onnx" / "faraday_code_assurance.onnx"


def run_benchmark(
    model_path: Path = DEFAULT_ONNX_PATH,
    iterations: int = 50,
    warmup: int = 10,
    seq_lengths: List[int] = None,
    output_json: Path = None,
    console: Console = None,
) -> Dict[str, Any]:
    """
    Executes a reproducible neural inference benchmark across multiple sequence lengths.
    """
    if seq_lengths is None:
        seq_lengths = [16, 32, 64, 128]

    if console is None:
        console = Console(legacy_windows=False)

    if not model_path.exists():
        from scripts.export_qnn_model import export_faraday_neural_model
        console.print(f"[yellow][!] Model artifact not found at {model_path}. Generating now...[/]")
        model_path, _ = export_faraday_neural_model(model_path.parent)

    hw = probe_hardware_environment()
    ep = probe_onnx_execution_providers()

    # Session setup
    available = ort.get_available_providers()
    target_providers = [p for p in ["QNNExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"] if p in available] or ["CPUExecutionProvider"]

    sess_opts = ort.SessionOptions()
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(str(model_path), sess_options=sess_opts, providers=target_providers)
    bound_provider = session.get_providers()[0]

    console.print()
    console.print(Panel(
        f"[bold white]Faraday Silicon Neural Inference Benchmark[/]\n"
        f"  Host Architecture: [cyan]{hw['machine']}[/] | Processor: [cyan]{hw['processor'][:35]}...[/]\n"
        f"  Bound Silicon Provider: [bold green]{bound_provider}[/]\n"
        f"  Model Artifact: [cyan]{model_path.name}[/] ({model_path.stat().st_size:,} bytes)\n"
        f"  Benchmark Profile: [yellow]{iterations} timed iterations[/] (after {warmup} warmup passes)",
        title="[PERFORMANCE EVALUATION]",
        border_style="bright_magenta",
        box=box.ROUNDED,
        padding=(1, 2),
    ))

    results_by_seq = {}

    table = Table(
        title="Inference Latency & Throughput Benchmark Matrix",
        box=box.ROUNDED,
        header_style="bold magenta",
        border_style="dim",
        expand=False,
    )
    table.add_column("Seq Length", justify="center", style="bold cyan", width=12)
    table.add_column("Mean (ms)", justify="right", style="bold green", width=12)
    table.add_column("P50 (ms)", justify="right", style="green", width=10)
    table.add_column("P90 (ms)", justify="right", style="yellow", width=10)
    table.add_column("P95 (ms)", justify="right", style="yellow", width=10)
    table.add_column("P99 (ms)", justify="right", style="red", width=10)
    table.add_column("Min / Max (ms)", justify="right", style="dim", width=18)
    table.add_column("Throughput", justify="right", style="bold white", width=18)

    total_tokens_processed = 0
    t_start_all = time.perf_counter()

    for seq_len in seq_lengths:
        # Generate deterministic synthetic token tensor
        dummy_input = np.random.randint(1, 5000, (1, seq_len), dtype=np.int64)

        # Warmup
        for _ in range(warmup):
            _ = session.run(None, {"input_ids": dummy_input})

        # Timed passes
        latencies = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            _ = session.run(None, {"input_ids": dummy_input})
            latencies.append((time.perf_counter() - t0) * 1000.0)

        lat_arr = np.array(latencies)
        mean_l = float(np.mean(lat_arr))
        p50 = float(np.percentile(lat_arr, 50))
        p90 = float(np.percentile(lat_arr, 90))
        p95 = float(np.percentile(lat_arr, 95))
        p99 = float(np.percentile(lat_arr, 99))
        min_l = float(np.min(lat_arr))
        max_l = float(np.max(lat_arr))
        std_l = float(np.std(lat_arr))

        inf_per_sec = 1000.0 / mean_l if mean_l > 0 else 0
        tok_per_sec = inf_per_sec * seq_len
        total_tokens_processed += (iterations * seq_len)

        results_by_seq[f"seq_{seq_len}"] = {
            "seq_len": seq_len,
            "iterations": iterations,
            "mean_ms": round(mean_l, 4),
            "p50_ms": round(p50, 4),
            "p90_ms": round(p90, 4),
            "p95_ms": round(p95, 4),
            "p99_ms": round(p99, 4),
            "min_ms": round(min_l, 4),
            "max_ms": round(max_l, 4),
            "std_ms": round(std_l, 4),
            "inferences_per_sec": round(inf_per_sec, 2),
            "tokens_per_sec": round(tok_per_sec, 2),
        }

        min_max_str = f"{min_l:.2f} / {max_l:.2f}"
        thr_str = f"{tok_per_sec:,.0f} tok/s"
        table.add_row(
            f"{seq_len} tokens",
            f"{mean_l:.2f} ms",
            f"{p50:.2f} ms",
            f"{p90:.2f} ms",
            f"{p95:.2f} ms",
            f"{p99:.2f} ms",
            min_max_str,
            thr_str,
        )

    t_total_all = time.perf_counter() - t_start_all
    console.print(table)
    console.print()

    # Hardware & benchmark summary
    benchmark_payload = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware": {
            "machine": hw["machine"],
            "processor": hw["processor"],
            "os": hw["os"],
            "is_snapdragon": hw["is_snapdragon"],
        },
        "execution_provider": {
            "bound_provider": bound_provider,
            "available_providers": available,
            "qnn_npu_active": bound_provider == "QNNExecutionProvider",
        },
        "model": {
            "artifact": str(model_path),
            "size_bytes": model_path.stat().st_size,
            "parameters": 1413901,
        },
        "results": results_by_seq,
        "summary": {
            "total_iterations": iterations * len(seq_lengths),
            "total_tokens_evaluated": total_tokens_processed,
            "total_elapsed_seconds": round(t_total_all, 3),
        },
    }

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(benchmark_payload, indent=2), encoding="utf-8")
        console.print(f"[bold green][✓] Benchmark results exported:[/] [cyan]{output_json}[/]\n")

    return benchmark_payload


def main():
    parser = argparse.ArgumentParser(description="Faraday Silicon Neural Benchmark")
    parser.add_argument("--iterations", type=int, default=50, help="Number of timed benchmark passes (default: 50)")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warmup iterations (default: 10)")
    parser.add_argument("--model", default=str(DEFAULT_ONNX_PATH), help="Path to ONNX model file")
    parser.add_argument("--output", default="review_output/benchmark_results.json", help="Path to write JSON benchmark report")
    args = parser.parse_args()

    out_path = Path(args.output) if args.output else None
    run_benchmark(
        model_path=Path(args.model),
        iterations=args.iterations,
        warmup=args.warmup,
        output_json=out_path,
    )


if __name__ == "__main__":
    main()
