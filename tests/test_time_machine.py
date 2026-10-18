"""
test_time_machine.py

Unit and integration tests for Faraday Time Machine:
1. Git blame porcelain parser.
2. Root-cause context analysis (explain_why_it_happened).
3. Minimal safe fix generator (suggest_minimal_safe_fix).
4. Full 5-stage timeline synthesis (INTRODUCED -> DETECTED -> REPRODUCED -> FIXED -> VERIFIED).
5. Serialization to dictionary/JSON.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from backend.core.time_machine import (
    CommitOrigin,
    TimeMachineResult,
    explain_why_it_happened,
    parse_git_blame_porcelain,
    suggest_minimal_safe_fix,
    trace_vulnerability,
)


def test_explain_why_it_happened():
    """Validates engineering explanations for standard CWEs."""
    why_sql = explain_why_it_happened("SEC-SQL01", "cursor.execute('SELECT * FROM users WHERE id = ' + uid)", "add user search")
    assert "parameterized SQL placeholder binding" in why_sql
    assert "add user search" in why_sql

    why_cmd = explain_why_it_happened("SEC-CMD01", "os.system('ping ' + host)", "network diagnostic")
    assert "subprocess argument list separation" in why_cmd

    why_path = explain_why_it_happened("SEC-PATH01", "open('/data/' + filename)", "file upload handler")
    assert "path containment validation" in why_path


def test_suggest_minimal_safe_fix():
    """Validates minimal safe remediations for vulnerabilities."""
    fix_sql = suggest_minimal_safe_fix("SEC-SQL01", "query = 'SELECT ...' + id")
    assert "parameterized placeholders" in fix_sql

    fix_cmd = suggest_minimal_safe_fix("SEC-CMD01", "os.system(cmd)")
    assert "subprocess.run" in fix_cmd
    assert "shell=False" in fix_cmd

    fix_deser = suggest_minimal_safe_fix("SEC-DESER01", "pickle.loads(data)")
    assert "json.loads" in fix_deser


def test_timeline_synthesis_with_mock_git(tmp_path: Path):
    """Verifies that trace_vulnerability builds the complete 5-stage timeline."""
    target_file = tmp_path / "vulnerable_app.py"
    target_file.write_text(
        'def get_user(uid):\n    query = "SELECT * FROM users WHERE id = " + uid\n    cursor.execute(query)\n',
        encoding="utf-8"
    )

    mock_blame = (
        "a1b2c3d4e5f6 2 2 1\n"
        "author Alice Smith\n"
        "author-mail <alice@enterprise.com>\n"
        "author-time 1715472000\n"
        "summary feat: add fast user search query\n"
        "\tquery = \"SELECT * FROM users WHERE id = \" + uid\n"
    )

    with patch("backend.core.time_machine._run_git") as mock_git:
        def git_side_effect(args, cwd):
            if args[0] == "blame":
                return mock_blame
            elif args[0] == "show":
                return "commit body details\n 1 file changed, 2 insertions(+)"
            return ""

        mock_git.side_effect = git_side_effect

        results = trace_vulnerability(tmp_path, "vulnerable_app.py", line_number=2)
        assert len(results) > 0
        r = results[0]

        assert r.rule_id == "SEC-SQL01"
        assert r.origin is not None
        assert r.origin.author == "Alice Smith"
        assert r.origin.author_email == "alice@enterprise.com"
        assert r.origin.short_hash == "a1b2c3d4"

        # Check 5-Stage Timeline
        stages = [step.stage for step in r.timeline]
        assert stages == ["INTRODUCED", "DETECTED", "REPRODUCED", "FIXED", "VERIFIED"]

        # Check dictionary serialization
        d = r.to_dict()
        assert d["rule_id"] == "SEC-SQL01"
        assert d["origin"]["author"] == "Alice Smith"
        assert len(d["timeline"]) == 5
