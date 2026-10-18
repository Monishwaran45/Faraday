"""
test_proof_engine.py

Unit and integration tests for Faraday Proof Engine & Proof-of-Fix 2.0:
1. Attack replay test synthesis.
2. Attack replay execution (pre-patch vs. post-patch).
3. Proof-of-Fix 2.0 interactive workflow.
4. Tamper-evident ProofOfFixEvidence digest computation.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from pathlib import Path
from rich.console import Console

from backend.core.proof_engine import (
    execute_replay_test,
    generate_attack_replay_test,
    run_proof_of_fix_2,
)


VULN_SQL = 'user_id = input("id: ")\nquery = "SELECT * FROM users WHERE id = " + user_id\n'
FIXED_SQL = 'user_id = input("id: ")\nquery = "SELECT * FROM users WHERE id = ?"\ncursor.execute(query, (user_id,))\n'


def test_generate_attack_replay_test():
    """Validates attack replay test synthesis for SQLi and Command Injection."""
    code_sql, payload_sql = generate_attack_replay_test("SEC-SQL01", "SELECT ... + id", "app.py")
    assert "test_sql_injection_defense" in code_sql
    assert "SQL injection escape vector" in payload_sql

    code_cmd, payload_cmd = generate_attack_replay_test("SEC-CMD01", "os.system(cmd)", "cmd.py")
    assert "test_command_injection_defense" in code_cmd


def test_execute_replay_test_pre_and_post_patch():
    """Verifies that pre-patch fails (reproduces vulnerability) and post-patch passes."""
    pre_result = execute_replay_test("SEC-SQL01", VULN_SQL, is_patched=False)
    assert pre_result.passed is False
    assert pre_result.status == "VULNERABILITY_REPRODUCED"

    post_result = execute_replay_test("SEC-SQL01", FIXED_SQL, is_patched=True)
    assert post_result.passed is True
    assert post_result.status == "FIX_VERIFIED"


def test_proof_of_fix_2_workflow_approved(tmp_path: Path):
    """Verifies complete Proof-of-Fix 2.0 execution with approved patch and evidence report."""
    target = tmp_path / "app.py"
    target.write_text(VULN_SQL, encoding="utf-8")
    console = Console(record=True, width=120)

    code, evidence = run_proof_of_fix_2(
        tmp_path,
        "app.py",
        FIXED_SQL,
        approve=lambda: True,
        console=console,
        output_dir=tmp_path / "review_output",
    )

    assert code == 0
    assert evidence is not None
    assert evidence.verification_verdict == "VERIFIED_FIX"
    assert evidence.static_rescan_clean is True
    assert len(evidence.tamper_evident_digest) == 64

    # Verify target file updated
    assert target.read_text(encoding="utf-8") == FIXED_SQL

    # Verify evidence JSON saved on disk
    evidence_file = tmp_path / "review_output" / "proof_of_fix_evidence_sec-sql01.json"
    assert evidence_file.exists()


def test_proof_of_fix_2_workflow_declined(tmp_path: Path):
    """Verifies that declining patch proposal leaves file unchanged."""
    target = tmp_path / "app.py"
    target.write_text(VULN_SQL, encoding="utf-8")
    console = Console(record=True, width=120)

    code, evidence = run_proof_of_fix_2(
        tmp_path,
        "app.py",
        FIXED_SQL,
        approve=lambda: False,
        console=console,
    )

    assert code == 1
    assert evidence is None
    assert target.read_text(encoding="utf-8") == VULN_SQL
