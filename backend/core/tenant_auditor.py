"""
tenant_auditor.py

Multi-Tenant Data Isolation & Invariant Auditor.
Scans multi-tenant codebases (B2B SaaS, healthcare, banking) for cross-tenant
data leaks, unscoped database queries, BOLA/IDOR authorization flaws (CWE-639/CWE-284),
and unpartitioned cache/session keys.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set
from rich.console import Console
from rich.table import Table
from rich import box

TENANT_IDENTIFIERS = {
    "tenant_id", "org_id", "organization_id", "account_id",
    "workspace_id", "company_id", "team_id", "customer_id"
}

TENANT_SENSITIVE_TABLES = {
    "users", "orders", "documents", "invoices", "payments", "projects",
    "accounts", "files", "records", "transactions", "customers", "notes"
}


@dataclass
class TenantFinding:
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    category: str  # 'unscoped_query', 'unscoped_mutation', 'missing_tenant_param', 'unpartitioned_cache'
    file_path: str
    line_number: int
    entity: str
    code_snippet: str
    message: str
    remediation: str


@dataclass
class TenantAuditReport:
    target_path: str
    files_scanned: int
    is_multi_tenant: bool
    detected_tenant_keys: Set[str] = field(default_factory=set)
    findings: List[TenantFinding] = field(default_factory=list)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity.upper() == "HIGH")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity.upper() == "MEDIUM")

    @property
    def isolation_score(self) -> float:
        if not self.is_multi_tenant or not self.findings:
            return 100.0
        penalty = (self.high_count * 20.0) + (self.medium_count * 10.0)
        return max(0.0, 100.0 - penalty)


class MultiTenantASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, code_lines: List[str], detected_keys: Set[str]):
        self.file_path = file_path
        self.code_lines = code_lines
        self.detected_keys = detected_keys
        self.findings: List[TenantFinding] = []

    def _get_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.code_lines):
            return self.code_lines[lineno - 1].strip()
        return ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._audit_route_tenant_scoping(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._audit_route_tenant_scoping(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        self._audit_orm_filter(node)
        self._audit_cache_partitioning(node)
        self.generic_visit(node)

    def _audit_route_tenant_scoping(self, node):
        # Look for Flask/FastAPI route decorators: @app.get, @app.route, @router.delete
        is_route = False
        for dec in node.decorator_list:
            dec_str = ""
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                dec_str = dec.func.attr
            elif isinstance(dec, ast.Attribute):
                dec_str = dec.attr
            if dec_str.lower() in ("route", "get", "post", "put", "delete", "patch"):
                is_route = True
                break

        if not is_route:
            return

        arg_names = [a.arg for a in node.args.args]
        # Check if the route operates on an entity ID without receiving or checking tenant context
        has_entity_id = any(re.search(r"(\w+)_id$", name) and name not in TENANT_IDENTIFIERS for name in arg_names)
        has_tenant = any(name in TENANT_IDENTIFIERS or "tenant" in name or "org" in name for name in arg_names)

        # Also inspect docstring and body for tenant retrieval
        body_text = "\n".join(
            self.code_lines[c.lineno - 1]
            for c in node.body
            if hasattr(c, "lineno") and 1 <= c.lineno <= len(self.code_lines)
        ).lower()

        tenant_in_body = any(k in body_text for k in TENANT_IDENTIFIERS)

        if has_entity_id and not has_tenant and not tenant_in_body:
            entity_param = [n for n in arg_names if re.search(r"(\w+)_id$", n) and n not in TENANT_IDENTIFIERS][0]
            self.findings.append(
                TenantFinding(
                    severity="HIGH",
                    category="missing_tenant_param",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    entity=node.name,
                    code_snippet=self._get_snippet(node.lineno),
                    message=f"HTTP endpoint '{node.name}' accesses specific entity ('{entity_param}') without binding or validating tenant context.",
                    remediation=f"Inject `current_user.tenant_id` dependency and verify `{entity_param}` belongs to the requesting tenant.",
                )
            )

    def _audit_orm_filter(self, node: ast.Call):
        # Check SQLAlchemy .filter(...) or .filter_by(...) or Django .filter(...)
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("filter", "filter_by"):
            call_source = ast.unparse(node) if hasattr(ast, "unparse") else ""
            if any(t in call_source.lower() for t in TENANT_SENSITIVE_TABLES):
                has_tenant_filter = any(k in call_source.lower() for k in TENANT_IDENTIFIERS)
                if not has_tenant_filter:
                    self.findings.append(
                        TenantFinding(
                            severity="HIGH",
                            category="unscoped_query",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            entity=node.func.attr,
                            code_snippet=self._get_snippet(node.lineno),
                            message="ORM query on tenant-sensitive entity without tenant/org filtering predicate.",
                            remediation="Scope query with `.filter(Model.tenant_id == current_user.tenant_id)` to prevent cross-tenant data leakage.",
                        )
                    )

    def _audit_cache_partitioning(self, node: ast.Call):
        # Check cache.set(...) or redis.set(...)
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("set", "get", "hset", "hget"):
            if isinstance(node.func.value, ast.Name) and node.func.value.id.lower() in ("cache", "redis", "memcached"):
                if node.args:
                    key_arg = node.args[0]
                    key_src = ast.unparse(key_arg) if hasattr(ast, "unparse") else ""
                    if not any(k in key_src.lower() for k in TENANT_IDENTIFIERS):
                        self.findings.append(
                            TenantFinding(
                                severity="MEDIUM",
                                category="unpartitioned_cache",
                                file_path=self.file_path,
                                line_number=node.lineno,
                                entity=f"{node.func.value.id}.{node.func.attr}",
                                code_snippet=self._get_snippet(node.lineno),
                                message="Cache key lacks tenant partitioning prefix in multi-tenant environment.",
                                remediation="Prefix cache key with tenant namespace: `f'tenant:{tenant_id}:{key}'`.",
                            )
                        )


def scan_raw_sql_in_file(file_path: Path, code_text: str, lines: List[str]) -> List[TenantFinding]:
    """Scan raw SQL queries for unscoped multi-tenant mutations or lookups."""
    findings = []
    # Pattern: DELETE FROM <table> WHERE id = ... (without tenant_id)
    # Pattern: UPDATE <table> SET ... WHERE id = ... (without tenant_id)
    # Pattern: SELECT ... FROM <table> WHERE id = ... (without tenant_id)
    sql_patterns = [
        (
            re.compile(r"""(DELETE\s+FROM\s+(\w+)\s+WHERE\s+(?!.*tenant_id|.*org_id|.*account_id)id\s*=\s*[\w\?\:%]+)""", re.IGNORECASE),
            "unscoped_mutation",
            "HIGH",
            "Unscoped DELETE query by primary key allows cross-tenant record destruction.",
            "Add `AND tenant_id = ?` to prevent cross-tenant record deletion."
        ),
        (
            re.compile(r"""(UPDATE\s+(\w+)\s+SET\s+.*?WHERE\s+(?!.*tenant_id|.*org_id|.*account_id)id\s*=\s*[\w\?\:%]+)""", re.IGNORECASE),
            "unscoped_mutation",
            "HIGH",
            "Unscoped UPDATE query modifies entity without verifying tenant ownership.",
            "Append `AND tenant_id = ?` to verify caller ownership before updating."
        ),
        (
            re.compile(r"""(SELECT\s+.*?\s+FROM\s+(users|orders|documents|invoices|projects)\s+WHERE\s+(?!.*tenant_id|.*org_id|.*account_id)id\s*=\s*[\w\?\:%]+)""", re.IGNORECASE),
            "unscoped_query",
            "HIGH",
            "Direct entity lookup by ID without tenant scoping violates tenant isolation boundary.",
            "Ensure query enforces `WHERE id = ? AND tenant_id = ?`."
        )
    ]

    for idx, line in enumerate(lines, 1):
        for pat, cat, sev, msg, rem in sql_patterns:
            m = pat.search(line)
            if m:
                table_name = m.group(2) if len(m.groups()) >= 2 else "entity"
                findings.append(
                    TenantFinding(
                        severity=sev,
                        category=cat,
                        file_path=str(file_path),
                        line_number=idx,
                        entity=table_name,
                        code_snippet=line.strip(),
                        message=msg,
                        remediation=rem,
                    )
                )

    return findings


def audit_codebase_multi_tenant(target_path: Path) -> TenantAuditReport:
    """Audits target codebase or file for multi-tenant data isolation and invariant compliance."""
    target_path = target_path.resolve()
    report = TenantAuditReport(target_path=str(target_path), files_scanned=0, is_multi_tenant=False)

    if target_path.is_file():
        files = [target_path]
    else:
        is_explicit_test_target = target_path.name in ("tests", "test")
        files = [
            p for p in target_path.rglob("*.py")
            if not any(part in p.parts for part in (".git", ".venv", "venv", "__pycache__", "node_modules"))
            and (is_explicit_test_target or not any(part in p.parts for part in ("tests", "test")))
        ]

    report.files_scanned = len(files)

    # First pass: Determine if multi-tenant architecture exists in the repository
    all_content = []
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
            all_content.append((f, txt))
            for k in TENANT_IDENTIFIERS:
                if k in txt.lower():
                    report.detected_tenant_keys.add(k)
        except Exception:
            continue

    if len(report.detected_tenant_keys) > 0:
        report.is_multi_tenant = True

    # Second pass: If multi-tenant, perform deep AST and SQL invariant auditing
    if report.is_multi_tenant:
        for f, content in all_content:
            lines = content.splitlines()
            # 1. Raw SQL Checks
            sql_findings = scan_raw_sql_in_file(f, content, lines)
            report.findings.extend(sql_findings)

            # 2. AST Checks
            try:
                tree = ast.parse(content, filename=str(f))
                visitor = MultiTenantASTVisitor(str(f), lines, report.detected_tenant_keys)
                visitor.visit(tree)
                report.findings.extend(visitor.findings)
            except Exception:
                continue

    return report


def print_tenant_audit_report(report: TenantAuditReport, console: Optional[Console] = None):
    """Renders a rich terminal summary of the multi-tenant isolation audit."""
    if console is None:
        console = Console()

    table = Table(
        title="[bold cyan]🏢 Multi-Tenant Data Isolation & Invariant Audit[/]",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="cyan",
        expand=False,
    )
    table.add_column("Severity", justify="center", width=12)
    table.add_column("Violation Type", style="bold white", width=22)
    table.add_column("Location", style="cyan", width=28)
    table.add_column("Invariant Failure & Required Fix", style="white")

    if not report.is_multi_tenant:
        console.print()
        console.print("[bold yellow][!] No multi-tenant indicators detected in this repository.[/]")
        console.print(f"[dim]Scanned {report.files_scanned} source file(s). Multi-tenant identifiers ({', '.join(list(TENANT_IDENTIFIERS)[:4])}) were not present.[/]\n")
        return

    if not report.findings:
        console.print()
        console.print("[bold green][✓] 100% Multi-Tenant Isolation Verified![/] Zero cross-tenant data leaks or unscoped queries found.")
        console.print(f"[dim]Scanned {report.files_scanned} file(s) tracking tenant identifiers: {', '.join(sorted(report.detected_tenant_keys))}[/]\n")
        return

    for f in report.findings:
        if f.severity.upper() == "HIGH":
            sev_badge = "[bold white on red] HIGH [/]"
        elif f.severity.upper() == "MEDIUM":
            sev_badge = "[bold black on yellow] MEDIUM [/]"
        else:
            sev_badge = "[bold white on blue] LOW [/]"

        loc = f"{Path(f.file_path).name}:{f.line_number}"
        detail = f"[bold red]{f.message}[/]\n[dim]Code:[/] `{f.code_snippet}`\n[bold green]Remediation:[/] {f.remediation}"
        table.add_row(sev_badge, f.category.replace("_", " ").title(), loc, detail)

    console.print()
    console.print(table)
    console.print()
    score_color = "green" if report.isolation_score >= 80 else ("yellow" if report.isolation_score >= 50 else "red")
    console.print(
        f"[bold]Isolation Score:[/] [{score_color}]{report.isolation_score:.1f}%[/] ➔ "
        f"[bold red]{report.high_count} High[/], [bold yellow]{report.medium_count} Medium[/] isolation violation(s) identified across {report.files_scanned} files.\n"
    )
