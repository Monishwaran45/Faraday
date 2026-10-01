"""
test_fuzz.py

Fuzz testing and resilience suite for Faraday.
Validates robust handling of adversarial, malformed, and edge-case inputs:
1. Tokenizer fuzzing (null bytes, corrupted encodings, massive token streams).
2. AST analyzer fuzzing (syntax errors, deep recursion, obfuscated code).
3. SARIF & SBOM generation fuzzing (empty, unicode, corrupted fields).

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import pytest
import numpy as np
from pathlib import Path
from backend.models.tokenizer import CodeTokenizer
from backend.core.ast_analyzer import analyze_python_ast
from backend.core.sbom import generate_cyclonedx_sbom, generate_spdx_sbom
from backend.core.sarif_builder import generate_sarif_report
from backend.core.finding import SecurityFinding


def test_fuzz_tokenizer_resilience():
    """Fuzzes tokenizer with null bytes, emojis, binary sequences, and large payloads."""
    tokenizer = CodeTokenizer.get_default()

    fuzz_inputs = [
        "",                                         # Empty
        "   \n\t   \r\n   ",                        # Whitespace only
        "\x00\x01\x02\x03\xff\xfe\xaa",            # Binary control bytes
        "def 🚀_function(🔥_param):\n    return 💯",  # Emojis / UTF-8 multibyte
        "a" * 50_000,                               # Massive single token
        "token " * 5_000,                           # 5,000 repeated words
        "\n".join(f"var_{i} = {i}" for i in range(1000)),  # Long AST sequence
    ]

    for item in fuzz_inputs:
        tensor = tokenizer.encode(item, max_length=64, padding=True)
        assert isinstance(tensor, np.ndarray)
        assert tensor.shape == (1, 64)
        assert tensor.dtype == np.int64
        # Invariant: Tokens must never breach embedding table boundary
        assert np.all(tensor >= 0)
        assert np.all(tensor < 10000)


def test_fuzz_ast_analyzer_syntax_error_resilience():
    """Validates that AST analyzer gracefully recovers from invalid Python syntax."""
    malformed_inputs = [
        "def invalid_syntax(:",
        "for i in",
        "import ;;;",
        "((((((((((",
        "return 42 outside function",
        "class A(A): pass",
        "while True: if: pass",
        "\x00\x00\x00def test(): pass",
    ]

    for code in malformed_inputs:
        # Must not raise unhandled exception
        findings = analyze_python_ast(code, file_path="fuzz_test.py")
        assert isinstance(findings, list)


def test_fuzz_sbom_generation_resilience():
    """Validates SBOM generation with malformed and empty component metadata."""
    corrupted_components = [
        {"name": "test-pkg", "version": "0.0.1"},
        {"name": "emoji-pkg-🔥", "version": "1.0.0", "license": "MIT/Apache-2.0"},
        {"name": "", "version": "", "license": None, "supplier": None},
        {"name": "null-byte-\x00", "version": "2.0.0", "purl": "pkg:generic/null"},
    ]

    cdx = generate_cyclonedx_sbom(corrupted_components)
    assert cdx["bomFormat"] == "CycloneDX"
    assert len(cdx["components"]) == 4

    spdx = generate_spdx_sbom(corrupted_components)
    assert spdx["spdxVersion"] == "SPDX-2.3"
    assert len(spdx["packages"]) == 4


def test_fuzz_sarif_builder_resilience():
    """Validates SARIF report generation against edge-case findings."""
    fuzz_finding = SecurityFinding(
        file_path="fuzz/path/to/script.py",
        line_number=-999,  # Negative line number edge case
        label="Fuzz Finding With \n Newlines \t And \"Quotes\"",
        severity="UNKNOWN_SEVERITY",
        snippet="snippet with \x00 null bytes and \u2603 snowman",
    )

    doc = generate_sarif_report([fuzz_finding], [], Path("."))
    assert doc["version"] == "2.1.0"
    assert len(doc["runs"][0]["results"]) == 1
    # Line number must be clamped to at least 1
    assert doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"] >= 1
