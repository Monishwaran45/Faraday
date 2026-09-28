"""
test_npu_inference.py

Comprehensive test suite verifying Qualcomm Snapdragon NPU tensor inference,
model graph integrity, provider fallback transparency, and diagnostic provers.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import json
from pathlib import Path

import onnx
import onnxruntime as ort
import numpy as np
import pytest

from backend.models.model_backend import QNNBackend, HeuristicRuleBackend, get_backend
from backend.models.verify_npu import (
    verify_npu_and_benchmark,
    probe_hardware_environment,
    probe_onnx_execution_providers,
)
from backend.core.doctor import check_npu_silicon, run_doctor
from scripts.benchmark_npu import run_benchmark


BASE_DIR = Path(__file__).resolve().parent.parent
ONNX_MODEL = BASE_DIR / "models" / "onnx" / "faraday_code_assurance.onnx"
MANIFEST_FILE = BASE_DIR / "models" / "onnx" / "qnn_compile_manifest.json"


def test_onnx_model_file_and_schema_validity():
    """Verify that the exported ONNX model exists, is valid, and matches the multi-head schema."""
    assert ONNX_MODEL.exists(), f"Model artifact missing at {ONNX_MODEL}"
    assert ONNX_MODEL.stat().st_size > 1_000_000, "ONNX model file size unexpectedly small"

    model = onnx.load(str(ONNX_MODEL))
    onnx.checker.check_model(model)

    graph = model.graph
    input_names = [inp.name for inp in graph.input]
    output_names = [out.name for out in graph.output]

    assert "input_ids" in input_names
    assert "risk_score" in output_names
    assert "severity_logits" in output_names
    assert "category_logits" in output_names


def test_qnn_compile_manifest_validity():
    """Verify the Qualcomm AI Hub compilation manifest targets Snapdragon X Elite."""
    assert MANIFEST_FILE.exists(), f"Manifest file missing at {MANIFEST_FILE}"
    content = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))

    assert content["model_name"] == "faraday_code_assurance"
    assert "sc8380xp" in content["target_hardware"] or "Snapdragon X Elite" in content["target_hardware"]
    assert "Hexagon" in content["npu_accelerator"]
    assert "w4a16" in content["quantization_profile"]
    assert "qai-hub compile" in content["aihub_compile_command"]
    assert content["status"] == "READY_FOR_QUALCOMM_AI_HUB_COMPILATION"


def test_hardware_prover_and_diagnostic_certificate():
    """Verify verify_npu_and_benchmark generates an empirical certificate with live tensor runs."""
    cert = verify_npu_and_benchmark(onnx_path=ONNX_MODEL, iterations=5)

    assert "hardware" in cert
    assert "execution_providers" in cert
    assert "benchmark_metrics" in cert
    assert "silicon_execution_status" in cert
    assert cert["is_genuine_neural_execution"] is True

    hw = cert["hardware"]
    assert "machine" in hw
    assert "processor" in hw
    assert "is_snapdragon" in hw

    bench = cert["benchmark_metrics"]
    assert bench["iterations"] == 5
    assert bench["mean_latency_ms"] > 0
    assert bench["min_latency_ms"] <= bench["max_latency_ms"]
    assert bench["predicted_severity"] in ["Clean", "Low", "Medium", "High"]
    assert 0.0 <= bench["sample_risk_score"] <= 1.0


def test_qnn_backend_real_tensor_execution():
    """Verify QNNBackend genuinely executes tensor inference and reports active provider."""
    backend = QNNBackend()

    assert backend.is_neural is True
    assert backend.active_provider in ("QNNExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider")

    # Verify deterministic token tensor generation
    tokens = backend.tokenize_code("def secure_connect(): pass", max_seq_len=64)
    assert isinstance(tokens, np.ndarray)
    assert tokens.shape == (1, 64)
    assert tokens.dtype == np.int64

    # Test generation with tensor execution
    prompt = "Code:\ndef query(id):\n    return db.execute('SELECT * FROM users WHERE id=' + id)\n"
    review = backend.generate(prompt)
    assert "ISSUES:" in review
    assert "SEVERITY:" in review
    assert "SUGGESTED_FIX:" in review


def test_heuristic_backend_explicit_label_and_non_neural():
    """Verify HeuristicRuleBackend never masquerades as neural or NPU execution."""
    backend = HeuristicRuleBackend()

    assert backend.is_neural is False
    assert backend.active_provider == "None (Deterministic Rule Engine)"
    assert "Rule-based Fallback — Non-Neural" in backend.name
    assert "deterministic" in backend.fallback_reason.lower()


def test_faraday_doctor_npu_audit():
    """Verify faraday doctor --npu diagnostics accurately audit silicon and runtime status."""
    npu_info = check_npu_silicon()

    assert npu_info["model_present"] is True
    assert npu_info["manifest_present"] is True
    assert npu_info["benchmark_ok"] is True
    assert npu_info["latency_ms"] > 0.0
    assert npu_info["active_provider"] in ("QNNExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider")


def test_reproducible_benchmark_execution(tmp_path):
    """Verify benchmark_npu runs across multiple sequence lengths and writes valid JSON."""
    out_json = tmp_path / "bench_test.json"
    data = run_benchmark(
        model_path=ONNX_MODEL,
        iterations=5,
        warmup=2,
        seq_lengths=[16, 32],
        output_json=out_json,
    )

    assert out_json.exists()
    assert "seq_16" in data["results"]
    assert "seq_32" in data["results"]
    assert data["results"]["seq_16"]["mean_ms"] > 0.0
    assert data["results"]["seq_32"]["tokens_per_sec"] > 0.0
    assert data["execution_provider"]["bound_provider"] in ("QNNExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider")
