"""
tests/test_hallucination_detector.py

Exhaustive tests for the AI Hallucination & Phantom API Detector module.
"""

from pathlib import Path
from backend.core.hallucination_detector import (
    audit_file_for_hallucinations,
    audit_codebase_hallucinations,
)


def test_detects_phantom_module_import(tmp_path: Path):
    code = """
import os
import sys
import fake_phantom_ai_security_lib_xyz

def do_work():
    return os.path.exists('.')
"""
    f = tmp_path / "phantom_import_test.py"
    f.write_text(code, encoding="utf-8")

    findings = audit_file_for_hallucinations(f, project_root=tmp_path)
    assert len(findings) == 1
    assert findings[0].category == "phantom_import"
    assert "fake_phantom_ai_security_lib_xyz" in findings[0].symbol_name
    assert findings[0].severity == "HIGH"


def test_detects_phantom_stdlib_method(tmp_path: Path):
    code = """
import hashlib

def verify_token(raw_bytes):
    # Phantom method hallucinated by AI
    return hashlib.validate(raw_bytes)
"""
    f = tmp_path / "phantom_method_test.py"
    f.write_text(code, encoding="utf-8")

    findings = audit_file_for_hallucinations(f, project_root=tmp_path)
    assert any(f.category == "phantom_method" and "hashlib.validate" in f.symbol_name for f in findings)


def test_detects_docstring_drift_hollow_security_claim(tmp_path: Path):
    code = """
def authenticate_request(payload, signature):
    \"\"\"
    Validates signature using HMAC-SHA256 and constant-time comparison.
    \"\"\"
    # Hollow body - zero cryptographic or HMAC checks
    return True
"""
    f = tmp_path / "drift_test.py"
    f.write_text(code, encoding="utf-8")

    findings = audit_file_for_hallucinations(f, project_root=tmp_path)
    assert any(f.category == "docstring_drift" and f.severity == "HIGH" for f in findings)


def test_detects_vacuous_ai_tests(tmp_path: Path):
    code = """
def test_user_authentication():
    # AI generated test with vacuous assertion
    assert True

def test_empty_suite():
    x = 1 + 1
"""
    f = tmp_path / "test_suite_sample.py"
    f.write_text(code, encoding="utf-8")

    findings = audit_file_for_hallucinations(f, project_root=tmp_path)
    assert len(findings) == 2
    assert all(f.category == "vacuous_test" for f in findings)


def test_clean_authentic_code_has_zero_hallucinations(tmp_path: Path):
    code = """
import hmac
import hashlib

def verify_hmac(key: bytes, msg: bytes, sig: bytes) -> bool:
    \"\"\"
    Validates signature using HMAC-SHA256 and constant-time comparison.
    \"\"\"
    expected = hmac.new(key, msg, hashlib.sha256).digest()
    return hmac.compare_digest(expected, sig)

def test_verify_hmac():
    k = b"secret"
    m = b"data"
    s = hmac.new(k, m, hashlib.sha256).digest()
    assert verify_hmac(k, m, s) is True
"""
    f = tmp_path / "clean_code.py"
    f.write_text(code, encoding="utf-8")

    report = audit_codebase_hallucinations(tmp_path)
    assert len(report.findings) == 0
    assert report.has_hallucinations is False
