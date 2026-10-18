"""
digital_twin.py

Faraday Codebase Digital Twin & X-Ray Impact Map:
Builds an evidence-backed static structural map of the codebase tracking:
- Symbol definitions (functions, classes, methods) with line spans.
- Function call graphs & callers.
- API route handlers (Flask, FastAPI, Express).
- Test suite coverage connections (tests touching specific functions).
- Security finding overlays.

Answers developer queries: "If I change function X, which endpoints and tests break?"

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from backend.core.file_scanner import scan_project
from backend.core.secret_scanner import scan_all


@dataclass
class CodeSymbol:
    """A function, method, or class discovered in the codebase."""
    name: str
    symbol_type: str         # "function", "method", "class"
    file_path: str
    start_line: int
    end_line: int
    docstring: str = ""
    calls: List[str] = field(default_factory=list)
    is_test: bool = False


@dataclass
class APIRoute:
    """An HTTP API endpoint detected via framework route decorators."""
    path: str
    http_methods: List[str]
    handler_symbol: str
    file_path: str
    line_number: int


@dataclass
class ImpactReport:
    """Evidence-backed impact analysis for a proposed code change."""
    target_symbol: str
    defined_at: Optional[CodeSymbol]
    direct_callers: List[Tuple[str, str, int]]    # (caller_symbol, file_path, line_no)
    transitive_callers: List[Tuple[str, str, int]]
    impacted_routes: List[APIRoute]
    impacted_tests: List[Tuple[str, str, int]]    # (test_func, file_path, line_no)
    active_findings: List[Tuple[str, str, int, str]] # (rule_id, severity, line_no, label)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_symbol": self.target_symbol,
            "defined_at": {
                "file_path": self.defined_at.file_path,
                "lines": f"{self.defined_at.start_line}-{self.defined_at.end_line}",
                "symbol_type": self.defined_at.symbol_type,
            } if self.defined_at else None,
            "direct_callers_count": len(self.direct_callers),
            "direct_callers": [
                {"caller": c[0], "file": c[1], "line": c[2]} for c in self.direct_callers
            ],
            "transitive_callers_count": len(self.transitive_callers),
            "impacted_routes_count": len(self.impacted_routes),
            "impacted_routes": [
                {"path": r.path, "methods": r.http_methods, "handler": r.handler_symbol, "file": r.file_path, "line": r.line_number}
                for r in self.impacted_routes
            ],
            "impacted_tests_count": len(self.impacted_tests),
            "impacted_tests": [
                {"test_function": t[0], "file": t[1], "line": t[2]} for t in self.impacted_tests
            ],
            "active_findings": [
                {"rule_id": f[0], "severity": f[1], "line": f[2], "label": f[3]} for f in self.active_findings
            ]
        }


class PythonASTVisitor(ast.NodeVisitor):
    """Walks Python AST to discover symbols, calls, and routes."""

    def __init__(self, relative_path: str):
        self.relative_path = relative_path.replace("\\", "/")
        self.symbols: List[CodeSymbol] = []
        self.routes: List[APIRoute] = []
        self.is_test_file = "test" in relative_path.lower()
        self._current_symbol: Optional[CodeSymbol] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_func(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_func(node, "function")

    def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, sym_type: str) -> None:
        doc = ast.get_docstring(node) or ""
        sym = CodeSymbol(
            name=node.name,
            symbol_type=sym_type,
            file_path=self.relative_path,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            docstring=doc.splitlines()[0] if doc else "",
            is_test=self.is_test_file or node.name.startswith("test_"),
        )

        # Detect route decorators: @app.route('/...'), @router.get('/...'), etc.
        for dec in node.decorator_list:
            route_path, methods = self._parse_route_decorator(dec)
            if route_path:
                self.routes.append(
                    APIRoute(
                        path=route_path,
                        http_methods=methods,
                        handler_symbol=node.name,
                        file_path=self.relative_path,
                        line_number=node.lineno,
                    )
                )

        # Record calls inside this function
        prev_symbol = self._current_symbol
        self._current_symbol = sym
        self.generic_visit(node)
        self._current_symbol = prev_symbol

        self.symbols.append(sym)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = ""
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            call_name = node.func.attr

        if call_name and self._current_symbol:
            self._current_symbol.calls.append(call_name)

        self.generic_visit(node)

    def _parse_route_decorator(self, dec: ast.AST) -> Tuple[Optional[str], List[str]]:
        """Extracts route path and HTTP methods from web framework decorators."""
        if isinstance(dec, ast.Call):
            attr_name = ""
            if isinstance(dec.func, ast.Attribute):
                attr_name = dec.func.attr.lower()
            elif isinstance(dec.func, ast.Name):
                attr_name = dec.func.id.lower()

            methods = ["GET"]
            if attr_name in ("get", "post", "put", "delete", "patch"):
                methods = [attr_name.upper()]

            route_path = ""
            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                route_path = dec.args[0].value

            for kw in dec.keywords:
                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    methods = [
                        elt.value
                        for elt in kw.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]

            if route_path:
                return route_path, methods

        return None, []


class CodebaseDigitalTwin:
    """Searchable in-memory representation of codebase symbols, routes, and call graph."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.symbols: Dict[str, List[CodeSymbol]] = {}     # symbol_name -> list of definitions
        self.routes: List[APIRoute] = []
        self.callers: Dict[str, Set[Tuple[str, str, int]]] = {} # callee_name -> {(caller, file, line)}
        self.findings_map: Dict[Tuple[str, int], List[Any]] = {}

    def add_symbol(self, sym: CodeSymbol) -> None:
        self.symbols.setdefault(sym.name, []).append(sym)
        for called in sym.calls:
            self.callers.setdefault(called, set()).add((sym.name, sym.file_path, sym.start_line))

    def add_route(self, route: APIRoute) -> None:
        self.routes.append(route)

    def query_impact(self, target_symbol: str) -> ImpactReport:
        """Computes downstream impact of altering target_symbol."""
        # 1. Locate primary definition
        defs = self.symbols.get(target_symbol, [])
        primary_def = defs[0] if defs else None

        # 2. Direct callers
        raw_direct = self.callers.get(target_symbol, set())
        direct_callers: List[Tuple[str, str, int]] = sorted(list(raw_direct), key=lambda x: (x[1], x[2]))

        # 3. Transitive callers (depth 2)
        transitive: Set[Tuple[str, str, int]] = set()
        for c_name, _, _ in direct_callers:
            for up in self.callers.get(c_name, set()):
                if up not in raw_direct and up[0] != target_symbol:
                    transitive.add(up)
        transitive_callers = sorted(list(transitive), key=lambda x: (x[1], x[2]))

        # 4. Impacted Routes
        all_affecting_symbols = {target_symbol} | {c[0] for c in direct_callers} | {c[0] for c in transitive_callers}
        impacted_routes = [
            r for r in self.routes if r.handler_symbol in all_affecting_symbols
        ]

        # 5. Impacted Tests
        impacted_tests = [
            c for c in direct_callers if c[0].startswith("test_") or "test" in c[1].lower()
        ]
        # Also check transitive tests
        for t in transitive_callers:
            if (t[0].startswith("test_") or "test" in t[1].lower()) and t not in impacted_tests:
                impacted_tests.append(t)

        # 6. Active security findings on target symbol lines
        active_findings: List[Tuple[str, str, int, str]] = []
        if primary_def:
            for (f_path, f_line), f_list in self.findings_map.items():
                if f_path == primary_def.file_path and primary_def.start_line <= f_line <= primary_def.end_line:
                    for item in f_list:
                        active_findings.append((item.rule_id, item.severity, item.line_number, item.label))

        return ImpactReport(
            target_symbol=target_symbol,
            defined_at=primary_def,
            direct_callers=direct_callers,
            transitive_callers=transitive_callers,
            impacted_routes=impacted_routes,
            impacted_tests=impacted_tests,
            active_findings=active_findings,
        )


def build_codebase_digital_twin(repo_root: Path | str) -> CodebaseDigitalTwin:
    """Builds an AST-powered Digital Twin of the given repository."""
    root = Path(repo_root).resolve()
    twin = CodebaseDigitalTwin(root)

    # 1. Scan and parse Python files
    for p in root.rglob("*.py"):
        # Skip virtualenvs and git
        parts = p.parts
        if any(ign in parts for ign in (".venv", "venv", ".git", "__pycache__", "build", "dist")):
            continue
        try:
            rel_p = str(p.relative_to(root)).replace("\\", "/")
            code_text = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(code_text, filename=str(p))
            visitor = PythonASTVisitor(rel_p)
            visitor.visit(tree)

            for sym in visitor.symbols:
                twin.add_symbol(sym)
            for rt in visitor.routes:
                twin.add_route(rt)
        except Exception:
            continue

    # 2. Populate security findings overlay
    try:
        scan_res = scan_project(str(root))
        findings = scan_all(scan_res.chunks)
        for f in findings:
            clean_path = str(f.file_path).replace("\\", "/")
            twin.findings_map.setdefault((clean_path, f.line_number), []).append(f)
    except Exception:
        pass

    return twin


def print_digital_twin_impact(report: ImpactReport, console: Optional[Console] = None) -> None:
    """Renders a beautiful Rich impact tree."""
    if console is None:
        console = Console(legacy_windows=False)

    console.print()
    banner = Panel(
        f"[bold cyan]🌐 FARADAY CODEBASE DIGITAL TWIN — CHANGE IMPACT MAP[/bold cyan]\n"
        f"[dim]Evidence-backed blast-radius query for symbol: '{report.target_symbol}'[/dim]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 2),
    )
    console.print(banner)
    console.print()

    # Definition Info
    if report.defined_at:
        console.print(
            f"[bold white]Target Symbol:[/] [bold green]{report.target_symbol}[/] "
            f"([cyan]{report.defined_at.symbol_type}[/]) at [cyan]{report.defined_at.file_path}:{report.defined_at.start_line}-{report.defined_at.end_line}[/]"
        )
        if report.defined_at.docstring:
            console.print(f"  [dim]Doc: {report.defined_at.docstring}[/]")
    else:
        console.print(f"[bold yellow]Notice:[/] Symbol '[bold red]{report.target_symbol}[/]' definition not indexed in repository source.")

    console.print()

    # Impact Tree
    root_tree = Tree(f"[bold cyan]Impact Blast Radius for [green]{report.target_symbol}[/]")

    # Branch 1: Direct Callers
    callers_branch = root_tree.add(f"[bold yellow]Direct Callers ({len(report.direct_callers)})[/]")
    for caller, file_p, line_no in report.direct_callers:
        callers_branch.add(f"[white]{caller}()[/] in [cyan]{file_p}:{line_no}[/]")

    # Branch 2: Transitive Callers
    if report.transitive_callers:
        trans_branch = root_tree.add(f"[dim]Upstream Transitive Callers ({len(report.transitive_callers)})[/]")
        for caller, file_p, line_no in report.transitive_callers:
            trans_branch.add(f"[dim]{caller}() in {file_p}:{line_no}[/]")

    # Branch 3: Impacted API Routes
    routes_branch = root_tree.add(f"[bold magenta]Impacted API Routes ({len(report.impacted_routes)})[/]")
    if report.impacted_routes:
        for r in report.impacted_routes:
            methods_str = ",".join(r.http_methods)
            routes_branch.add(f"[bold green]{methods_str} {r.path}[/] via handler [cyan]{r.handler_symbol}()[/] ({r.file_path}:{r.line_number})")
    else:
        routes_branch.add("[dim]No public HTTP API route directly depends on this symbol[/]")

    # Branch 4: Impacted Tests
    tests_branch = root_tree.add(f"[bold green]Impacted Test Suites ({len(report.impacted_tests)})[/]")
    if report.impacted_tests:
        for t_func, file_p, line_no in report.impacted_tests:
            tests_branch.add(f"[bold green]{t_func}()[/] in [cyan]{file_p}:{line_no}[/]")
    else:
        tests_branch.add("[bold yellow]⚠️ No existing automated test functions call this symbol directly![/]")

    # Branch 5: Security Findings Overlay
    if report.active_findings:
        findings_branch = root_tree.add(f"[bold red]Active Security Findings on Symbol ({len(report.active_findings)})[/]")
        for rule_id, sev, line_no, lbl in report.active_findings:
            findings_branch.add(f"[bold red]{rule_id}[/] ({sev}) line {line_no}: {lbl}")

    console.print(root_tree)
    console.print()
