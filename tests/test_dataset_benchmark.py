"""
test_dataset_benchmark.py

Unit tests for Faraday external dataset evaluation and multi-tool benchmark comparison.
Validates OWASP, Juliet, and SARD dataset profiles and metrics calculations.
"""

import pytest
from backend.core.dataset_benchmark import (
    evaluate_dataset,
    run_all_dataset_benchmarks,
    BENCHMARK_PROFILES,
    TOOL_COMPARISON_MATRIX,
)


def test_evaluate_dataset_owasp():
    result = evaluate_dataset("owasp")
    assert result["dataset"] == "owasp"
    assert result["files_analyzed"] == 2740
    assert result["true_positives"] == 1288
    assert result["precision"] > 90.0
    assert result["recall"] > 90.0
    assert result["f1"] > 90.0
    assert result["fpr"] < 10.0


def test_evaluate_dataset_juliet():
    result = evaluate_dataset("juliet")
    assert result["dataset"] == "juliet"
    assert result["files_analyzed"] == 3200
    assert result["precision"] >= 93.0
    assert result["f1"] >= 93.0


def test_evaluate_dataset_sard():
    result = evaluate_dataset("sard")
    assert result["dataset"] == "sard"
    assert result["files_analyzed"] == 1850
    assert result["precision"] >= 90.0


def test_evaluate_dataset_invalid():
    with pytest.raises(ValueError, match="Unknown benchmark dataset"):
        evaluate_dataset("non_existent_dataset")


def test_tool_comparison_matrix():
    assert len(TOOL_COMPARISON_MATRIX) == 4
    tools = [t["tool"] for t in TOOL_COMPARISON_MATRIX]
    assert any("Faraday" in t for t in tools)
    assert any("Semgrep" in t for t in tools)
    assert any("CodeQL" in t for t in tools)
    assert any("Bandit" in t for t in tools)
