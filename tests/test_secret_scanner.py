import pytest
from backend.core.file_scanner import CodeChunk
from backend.core.secret_scanner import scan_chunk, scan_all

def test_secret_scanner_detects_aws_key():
    chunk = CodeChunk(
        file_path="config.py",
        language="python",
        name="<module_level>",
        start_line=1,
        end_line=2,
        code='AWS_KEY = "AKIA1234567890ABCDEF"\n',
    )
    findings = scan_chunk(chunk)
    assert len(findings) >= 1
    assert any("AWS Access Key" in f.label for f in findings)
    assert findings[0].severity == "High"

def test_secret_scanner_detects_sql_injection():
    chunk = CodeChunk(
        file_path="db.py",
        language="python",
        name="get_user",
        start_line=10,
        end_line=14,
        code='query = "SELECT * FROM users WHERE id = " + user_id\n',
    )
    findings = scan_chunk(chunk)
    assert any("SQL String Concatenation" in f.label for f in findings)

def test_secret_scanner_detects_eval():
    chunk = CodeChunk(
        file_path="util.py",
        language="python",
        name="run_raw",
        start_line=20,
        end_line=22,
        code='eval(user_code)\n',
    )
    findings = scan_chunk(chunk)
    assert any("eval()" in f.label for f in findings)
