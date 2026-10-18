"""
test_digital_twin.py

Unit tests for Faraday Codebase Digital Twin:
1. AST symbol indexing (functions, classes).
2. API route mapping (Flask, FastAPI).
3. Reverse call-graph indexing (callers).
4. Evidence-backed blast radius and impact query.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from pathlib import Path
from backend.core.digital_twin import build_codebase_digital_twin


SAMPLE_APP = '''
def hash_password(raw_password):
    return "hashed_" + raw_password

def authenticate_user(username, password):
    hashed = hash_password(password)
    return username == "admin" and hashed == "hashed_secret"

@app.route("/api/login", methods=["POST"])
def login_endpoint(request):
    return authenticate_user(request.user, request.password)
'''

SAMPLE_TEST = '''
from app import authenticate_user

def test_login_flow():
    assert authenticate_user("admin", "secret") is True
'''


def test_codebase_digital_twin_indexing_and_impact(tmp_path: Path):
    """Verifies that the Digital Twin correctly links functions, callers, routes, and tests."""
    app_file = tmp_path / "app.py"
    app_file.write_text(SAMPLE_APP, encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_auth.py"
    test_file.write_text(SAMPLE_TEST, encoding="utf-8")

    twin = build_codebase_digital_twin(tmp_path)

    # 1. Verify symbols indexed
    assert "hash_password" in twin.symbols
    assert "authenticate_user" in twin.symbols
    assert len(twin.routes) >= 1
    assert twin.routes[0].path == "/api/login"

    # 2. Query impact of modifying 'hash_password'
    report = twin.query_impact("hash_password")
    assert report.target_symbol == "hash_password"
    assert report.defined_at is not None
    assert report.defined_at.file_path == "app.py"

    # Direct caller must be authenticate_user
    direct_caller_names = [c[0] for c in report.direct_callers]
    assert "authenticate_user" in direct_caller_names

    # Route impact check: /api/login depends on authenticate_user -> hash_password
    impacted_route_paths = [r.path for r in report.impacted_routes]
    assert "/api/login" in impacted_route_paths

    # Test impact check: test_login_flow touches authenticate_user
    test_names = [t[0] for t in report.impacted_tests]
    assert "test_login_flow" in test_names
