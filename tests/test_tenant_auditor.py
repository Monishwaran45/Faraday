"""
tests/test_tenant_auditor.py

Exhaustive tests for Multi-Tenant Data Isolation & Invariant Auditor.
"""

from pathlib import Path
from backend.core.tenant_auditor import audit_codebase_multi_tenant


def test_detects_unscoped_sql_mutation(tmp_path: Path):
    code = """
# Multi-tenant context present in codebase
CURRENT_TENANT = "tenant_id"

def delete_user_order(conn, order_id):
    # Unscoped DELETE allows cross-tenant deletion
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
"""
    f = tmp_path / "orders.py"
    f.write_text(code, encoding="utf-8")

    report = audit_codebase_multi_tenant(tmp_path)
    assert report.is_multi_tenant is True
    assert any(f.category == "unscoped_mutation" and f.severity == "HIGH" for f in report.findings)


def test_detects_unscoped_route_handler(tmp_path: Path):
    code = """
tenant_id = None

@app.route("/api/documents/<doc_id>")
def get_document(doc_id):
    # Accesses specific entity without binding tenant
    return fetch_from_db(doc_id)
"""
    f = tmp_path / "routes.py"
    f.write_text(code, encoding="utf-8")

    report = audit_codebase_multi_tenant(tmp_path)
    assert any(f.category == "missing_tenant_param" for f in report.findings)


def test_clean_tenant_scoped_code_passes(tmp_path: Path):
    code = """
def get_tenant_order(conn, tenant_id, order_id):
    query = "SELECT * FROM orders WHERE id = ? AND tenant_id = ?"
    return conn.execute(query, (order_id, tenant_id)).fetchall()

def delete_tenant_order(conn, tenant_id, order_id):
    query = "DELETE FROM orders WHERE id = ? AND tenant_id = ?"
    return conn.execute(query, (order_id, tenant_id))
"""
    f = tmp_path / "scoped_service.py"
    f.write_text(code, encoding="utf-8")

    report = audit_codebase_multi_tenant(tmp_path)
    assert report.is_multi_tenant is True
    assert len(report.findings) == 0
    assert report.isolation_score == 100.0


def test_single_tenant_project_skips_audit(tmp_path: Path):
    code = """
def calculate_fibonacci(n):
    return n if n <= 1 else calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
"""
    f = tmp_path / "math_utils.py"
    f.write_text(code, encoding="utf-8")

    report = audit_codebase_multi_tenant(tmp_path)
    assert report.is_multi_tenant is False
    assert len(report.findings) == 0
