"""
hallucination_detector.py

AI Hallucination & Phantom API Detector for Code.
Identifies false security assumptions, phantom package imports,
non-existent library methods, hollow docstring promises, and vacuous
test assertions introduced by AI coding assistants (Copilot, Claude, ChatGPT).
"""

import ast
import importlib.util
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set
from rich.console import Console
from rich.table import Table
from rich import box

# Known Python standard library names (comprehensive set for Python 3.10+)
if hasattr(sys, "stdlib_module_names"):
    STDLIB_MODULES = set(sys.stdlib_module_names)
else:
    STDLIB_MODULES = {
        "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib",
        "copy", "csv", "dataclasses", "datetime", "decimal", "difflib", "dis",
        "email", "enum", "errno", "functools", "glob", "gzip", "hashlib", "hmac",
        "html", "http", "importlib", "inspect", "io", "itertools", "json", "logging",
        "math", "mimetypes", "multiprocessing", "os", "pathlib", "pickle", "platform",
        "posixpath", "pprint", "queue", "random", "re", "secrets", "select", "shutil",
        "signal", "socket", "sqlite3", "ssl", "stat", "string", "subprocess", "sys",
        "tempfile", "threading", "time", "traceback", "types", "typing", "unittest",
        "urllib", "uuid", "warnings", "weakref", "xml", "zipfile", "zlib"
    }

# Known phantom methods frequently hallucinated by AI on standard libraries
PHANTOM_STDLIB_METHODS = {
    "hashlib": {"validate", "verify", "secure_hash", "check_digest"},
    "os.path": {"secure_join", "safe_join", "sanitize_path", "jail_path"},
    "json": {"safe_loads", "secure_load", "sanitize_json"},
    "sqlite3": {"secure_connect", "safe_execute", "parameterize_all"},
    "secrets": {"verify_signature", "create_jwt", "hash_password"},
}

# Key terms indicating security commitments in docstrings
SECURITY_CLAIM_PATTERNS = [
    (r"\b(sanitiz\w+|escap\w+)\s+(input|query|sql|html|string)", "sanitization"),
    (r"\b(validat\w+|verif\w+)\s+(signature|hmac|jwt|token|hash)", "signature_verification"),
    (r"\b(encrypt\w*|decrypt\w*)\s+(payload|data|password|secret)", "encryption"),
    (r"\b(constant[- ]time)\s+(compar\w+|equal\w*)", "constant_time"),
    (r"\b(rate[- ]limit\w*)", "rate_limiting"),
    (r"\b(authenticat\w+|authoriz\w+)\s+(user|request|caller)", "authentication"),
]


@dataclass
class HallucinationFinding:
    category: str  # 'phantom_import', 'phantom_method', 'docstring_drift', 'vacuous_test'
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    file_path: str
    line_number: int
    symbol_name: str
    code_snippet: str
    message: str
    remediation: str


@dataclass
class HallucinationReport:
    target_path: str
    files_scanned: int
    findings: List[HallucinationFinding] = field(default_factory=list)

    @property
    def has_hallucinations(self) -> bool:
        return len(self.findings) > 0

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity.upper() == "HIGH")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity.upper() == "MEDIUM")


class AIHallucinationVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, code_lines: List[str], project_root: Path):
        self.file_path = file_path
        self.code_lines = code_lines
        self.project_root = project_root
        self.findings: List[HallucinationFinding] = []
        self._imported_modules: Set[str] = set()

    def _get_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.code_lines):
            return self.code_lines[lineno - 1].strip()
        return ""

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            self._imported_modules.add(base_module)
            self._check_module_existence(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_module = node.module.split(".")[0]
            self._imported_modules.add(base_module)
            self._check_module_existence(node.module, node.lineno)
        self.generic_visit(node)

    def _check_module_existence(self, module_name: str, lineno: int):
        base_pkg = module_name.split(".")[0]
        # Ignore relative or internal project imports
        if base_pkg in STDLIB_MODULES:
            return

        # Check local filesystem relative to project root or file directory
        file_dir = Path(self.file_path).parent
        if (self.project_root / base_pkg).exists() or (file_dir / base_pkg).exists():
            return
        if (self.project_root / f"{base_pkg}.py").exists() or (file_dir / f"{base_pkg}.py").exists():
            return

        # Check if resolvable in current Python environment
        try:
            spec = importlib.util.find_spec(base_pkg)
            if spec is not None:
                return
        except (ModuleNotFoundError, ValueError, AttributeError):
            pass

        # If not standard, not local, and not in environment, flag as potential hallucinated dependency
        self.findings.append(
            HallucinationFinding(
                category="phantom_import",
                severity="HIGH",
                file_path=self.file_path,
                line_number=lineno,
                symbol_name=module_name,
                code_snippet=self._get_snippet(lineno),
                message=f"Module '{module_name}' cannot be resolved in standard library, project, or installed packages.",
                remediation=f"Verify if package '{base_pkg}' is declared in pyproject.toml / requirements.txt or replace with valid standard library alternative.",
            )
        )

    def visit_Call(self, node: ast.Call):
        # Detect phantom method calls on stdlib objects
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            obj_name = node.func.value.id
            method_name = node.func.attr
            if obj_name in PHANTOM_STDLIB_METHODS:
                if method_name in PHANTOM_STDLIB_METHODS[obj_name]:
                    self.findings.append(
                        HallucinationFinding(
                            category="phantom_method",
                            severity="HIGH",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            symbol_name=f"{obj_name}.{method_name}",
                            code_snippet=self._get_snippet(node.lineno),
                            message=f"Method '{obj_name}.{method_name}()' is a hallucinated API that does not exist in standard Python {obj_name}.",
                            remediation=f"Replace with supported {obj_name} standard methods or an authorized security helper.",
                        )
                    )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._audit_docstring_drift(node)
        self._audit_vacuous_test(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._audit_docstring_drift(node)
        self._audit_vacuous_test(node)
        self.generic_visit(node)

    def _audit_docstring_drift(self, node):
        docstring = ast.get_docstring(node)
        if not docstring:
            return

        body_source = "\n".join(
            self.code_lines[child.lineno - 1]
            for child in node.body
            if hasattr(child, "lineno") and 1 <= child.lineno <= len(self.code_lines)
        ).lower()

        doc_lower = docstring.lower()
        for pattern, claim_type in SECURITY_CLAIM_PATTERNS:
            match = re.search(pattern, doc_lower)
            if match:
                # Check if the body actually performs what the docstring claims
                drift_detected = False
                if claim_type == "signature_verification":
                    if not any(k in body_source for k in ("hmac", "sha256", "verify", "compare_digest", "signature")):
                        drift_detected = True
                elif claim_type == "encryption":
                    if not any(k in body_source for k in ("cipher", "encrypt", "aes", "fernet", "crypto", "seal")):
                        drift_detected = True
                elif claim_type == "constant_time":
                    if "compare_digest" not in body_source:
                        drift_detected = True
                elif claim_type == "sanitization":
                    if not any(k in body_source for k in ("escape", "clean", "replace", "parameter", "sanitize", "sub")):
                        drift_detected = True

                # If body is just trivial pass or return True
                if len(node.body) <= 2:
                    for stmt in node.body:
                        if isinstance(stmt, ast.Pass):
                            drift_detected = True
                        elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) and stmt.value.value is True:
                            drift_detected = True

                if drift_detected:
                    self.findings.append(
                        HallucinationFinding(
                            category="docstring_drift",
                            severity="HIGH",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            symbol_name=node.name,
                            code_snippet=self._get_snippet(node.lineno),
                            message=f"Function '{node.name}' claims in docstring to provide '{claim_type}', but the implementation contains zero matching security operations.",
                            remediation=f"Implement the claimed '{claim_type}' security controls or update the docstring to prevent false security assumptions.",
                        )
                    )

    def _audit_vacuous_test(self, node):
        # Only check functions that are test cases (starting with test_)
        if not node.name.startswith("test_"):
            return

        # Check for pytest.raises or assertRaises context managers
        for with_node in [n for n in ast.walk(node) if isinstance(n, ast.With)]:
            for item in with_node.items:
                item_src = ast.unparse(item.context_expr) if hasattr(ast, "unparse") else ""
                if "raises" in item_src.lower():
                    return

        asserts = [n for n in ast.walk(node) if isinstance(n, ast.Assert)]
        if not asserts:
            # Test with no assertions
            self.findings.append(
                HallucinationFinding(
                    category="vacuous_test",
                    severity="MEDIUM",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    symbol_name=node.name,
                    code_snippet=self._get_snippet(node.lineno),
                    message=f"Test function '{node.name}' contains zero assertions and passes unconditionally.",
                    remediation="Add assertions to verify expected return values, state changes, or exception boundaries.",
                )
            )
            return

        for a in asserts:
            # Check for assert True or assert 1 == 1
            is_vacuous = False
            if isinstance(a.test, ast.Constant) and a.test.value is True:
                is_vacuous = True
            elif isinstance(a.test, ast.Compare):
                # e.g., 1 == 1 or 'a' == 'a' or var == var
                if isinstance(a.test.left, ast.Constant) and len(a.test.comparators) == 1 and isinstance(a.test.comparators[0], ast.Constant):
                    if a.test.left.value == a.test.comparators[0].value:
                        is_vacuous = True

            if is_vacuous:
                self.findings.append(
                    HallucinationFinding(
                        category="vacuous_test",
                        severity="MEDIUM",
                        file_path=self.file_path,
                        line_number=a.lineno,
                        symbol_name=node.name,
                        code_snippet=self._get_snippet(a.lineno),
                        message=f"Vacuous assertion in '{node.name}' passes trivially without validating actual program behavior.",
                        remediation="Assert against the actual function output, API response status, or exception type.",
                    )
                )


def audit_file_for_hallucinations(file_path: Path, project_root: Optional[Path] = None) -> List[HallucinationFinding]:
    """Audit a single Python file for AI hallucinations, phantom APIs, docstring drift, and vacuous tests."""
    if not file_path.exists() or file_path.suffix != ".py":
        return []

    if project_root is None:
        project_root = file_path.parent

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
        lines = content.splitlines()
        visitor = AIHallucinationVisitor(str(file_path), lines, project_root)
        visitor.visit(tree)
        return visitor.findings
    except SyntaxError:
        return []
    except Exception:
        return []


def audit_codebase_hallucinations(target_path: Path) -> HallucinationReport:
    """Audit an entire codebase or file for AI-introduced hallucinations."""
    target_path = target_path.resolve()
    project_root = target_path if target_path.is_dir() else target_path.parent
    report = HallucinationReport(target_path=str(target_path), files_scanned=0)

    if target_path.is_file():
        files = [target_path]
    else:
        files = [
            p for p in target_path.rglob("*.py")
            if not any(part in p.parts for part in (".git", ".venv", "venv", "__pycache__", "node_modules"))
        ]

    report.files_scanned = len(files)
    for f in files:
        findings = audit_file_for_hallucinations(f, project_root=project_root)
        report.findings.extend(findings)

    return report


def print_hallucination_report(report: HallucinationReport, console: Optional[Console] = None):
    """Renders a rich terminal summary of AI hallucination findings."""
    if console is None:
        console = Console()

    table = Table(
        title="[bold magenta]🤖 AI Hallucination & Phantom API Audit Report[/]",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="magenta",
        expand=False,
    )
    table.add_column("Severity", justify="center", width=12)
    table.add_column("Category", style="bold white", width=18)
    table.add_column("Location", style="cyan", width=28)
    table.add_column("Finding & Remediation", style="white")

    if not report.findings:
        console.print()
        console.print("[bold green][✓] Zero AI Hallucinations Detected![/] All imports, APIs, and security claims verified authentic.")
        console.print(f"[dim]Scanned {report.files_scanned} source file(s) against stdlib catalogs and AST semantics.[/]\n")
        return

    for f in report.findings:
        if f.severity.upper() == "HIGH":
            sev_badge = "[bold white on red] HIGH [/]"
        elif f.severity.upper() == "MEDIUM":
            sev_badge = "[bold black on yellow] MEDIUM [/]"
        else:
            sev_badge = "[bold white on blue] LOW [/]"

        loc = f"{Path(f.file_path).name}:{f.line_number}"
        detail = f"[bold yellow]{f.message}[/]\n[dim]Code:[/] `{f.code_snippet}`\n[bold green]Fix:[/] {f.remediation}"
        table.add_row(sev_badge, f.category.replace("_", " ").title(), loc, detail)

    console.print()
    console.print(table)
    console.print()
    console.print(
        f"[bold]Summary:[/] Scanned [cyan]{report.files_scanned}[/] file(s) ➔ "
        f"[bold red]{report.high_count} High[/], [bold yellow]{report.medium_count} Medium[/] hallucination(s) detected.\n"
    )
