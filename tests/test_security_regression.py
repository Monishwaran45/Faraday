"""
test_security_regression.py

Automated Security Regression & Safe-Code Benchmark Suite for Faraday.
Validates true positive detection on known vulnerable patterns AND
verifies zero false positives on safe/remediated code equivalents.
Calculates Precision, Recall, and F1 Score for continuous quality assurance.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import pytest
from backend.core.file_scanner import CodeChunk
from backend.core.secret_scanner import scan_chunk
from backend.models.model_backend import get_backend

REGRESSION_CORPUS = [
    {
        "id": "SEC-SQL01",
        "name": "SQL Injection (CWE-89)",
        "vuln_code": """
def get_user(request):
    user_id = request.args.get('id')
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
""",
        "safe_code": """
def get_user(request):
    user_id = request.args.get('id')
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
""",
        "lang": "python"
    },
    {
        "id": "SEC-CMD01",
        "name": "Command Injection (CWE-78)",
        "vuln_code": """
import os
def ping_host(request):
    host = request.args.get('host')
    os.system("ping -c 1 " + host)
""",
        "safe_code": """
import subprocess
def ping_host(request):
    host = request.args.get('host')
    subprocess.run(["ping", "-c", "1", host], shell=False, check=True)
""",
        "lang": "python"
    },
    {
        "id": "SEC-EVAL01",
        "name": "Dynamic Code Evaluation (CWE-95)",
        "vuln_code": """
def evaluate_calc(request):
    expr = request.args.get('calc')
    return eval(expr)
""",
        "safe_code": """
import ast
def evaluate_calc(request):
    expr = request.args.get('calc')
    return ast.literal_eval(expr)
""",
        "lang": "python"
    },
    {
        "id": "SEC-DESER01",
        "name": "Insecure Deserialization (CWE-502)",
        "vuln_code": """
import pickle
def load_session(payload):
    return pickle.loads(payload)
""",
        "safe_code": """
import json
def load_session(payload):
    return json.loads(payload)
""",
        "lang": "python"
    },
    {
        "id": "SEC-XSS01",
        "name": "Cross-Site Scripting (CWE-79)",
        "vuln_code": """
function renderUser(user) {
    document.getElementById("profile").innerHTML = "<b>" + user.bio + "</b>";
}
""",
        "safe_code": """
function renderUser(user) {
    document.getElementById("profile").textContent = user.bio;
}
""",
        "lang": "javascript"
    },
    {
        "id": "SEC-RAND01",
        "name": "Insecure Randomness for Tokens (CWE-330)",
        "vuln_code": """
import random
def generate_auth_token():
    return "".join(random.choice("0123456789ABCDEF") for _ in range(32))
""",
        "safe_code": """
import secrets
def generate_auth_token():
    return secrets.token_hex(16)
""",
        "lang": "python"
    },
]


def test_regression_vulnerable_and_safe_pairs():
    """
    Automated regression:
    - Every vulnerable case MUST be detected (True Positive).
    - Every safe equivalent MUST NOT trigger false positives (True Negative).
    """
    tp = 0  # True Positives
    fn = 0  # False Negatives
    fp = 0  # False Positives
    tn = 0  # True Negatives
    backend = get_backend()

    for item in REGRESSION_CORPUS:
        # 1. Test Vulnerable Code
        v_chunk = CodeChunk(
            file_path=f"sample_{item['id']}.{ 'js' if item['lang'] == 'javascript' else 'py' }",
            language=item["lang"],
            name="vulnerable_sample",
            start_line=1,
            end_line=len(item["vuln_code"].splitlines()),
            code=item["vuln_code"],
        )
        static_findings = scan_chunk(v_chunk)
        ai_review = backend.generate(f"You are a senior reviewer for {item['lang']}.\nCode:\n{item['vuln_code']}")

        is_detected = (
            len(static_findings) > 0 or
            ("ISSUES:" in ai_review and "None found" not in ai_review)
        )

        if is_detected:
            tp += 1
        else:
            fn += 1

        assert is_detected, f"False Negative: {item['name']} was not detected in vulnerable sample!"

        # 2. Test Safe Equivalent Code
        s_chunk = CodeChunk(
            file_path=f"safe_{item['id']}.{ 'js' if item['lang'] == 'javascript' else 'py' }",
            language=item["lang"],
            name="safe_sample",
            start_line=1,
            end_line=len(item["safe_code"].splitlines()),
            code=item["safe_code"],
        )
        safe_findings = scan_chunk(s_chunk)
        safe_ai_review = backend.generate(f"You are a senior reviewer for {item['lang']}.\nCode:\n{item['safe_code']}")

        is_clean = (
            len(safe_findings) == 0 and
            ("None found" in safe_ai_review or "ISSUES:" not in safe_ai_review)
        )

        if is_clean:
            tn += 1
        else:
            fp += 1

        assert is_clean, f"False Positive: {item['name']} triggered finding in safe sample! Findings: {safe_findings}"

    # Calculate Benchmark Metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0

    print(f"\n[BENCHMARK] Precision: {precision * 100:.1f}%, Recall: {recall * 100:.1f}%, F1: {f1:.3f}, FPR: {fpr * 100:.1f}%")
    assert precision >= 0.95
    assert recall >= 0.95
    assert f1 >= 0.95
    assert fpr == 0.0
