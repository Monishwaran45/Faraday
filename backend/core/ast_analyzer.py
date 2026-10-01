"""
ast_analyzer.py

AST-Aware Static Analysis and Source-to-Sink Data-Flow Taint Tracking for Faraday.
Performs semantic data-flow analysis through abstract syntax trees to trace
untrusted inputs (sources) to dangerous execution points (sinks) with zero false
positives from comments, docstrings, or string literals.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import ast
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from backend.core.finding import SecurityFinding

TAINT_SOURCES = {
    # Web Frameworks (Flask, Django, FastAPI)
    "request.args", "request.form", "request.values", "request.json",
    "request.data", "request.params", "request.get", "request.post",
    "request.query_params", "request.body",
    # CLI & Environment
    "sys.argv", "input", "os.environ", "os.getenv",
}

SQL_SINKS = {
    "execute", "executemany", "raw", "select",
}

COMMAND_SINKS = {
    "os.system", "os.popen"
}

EVAL_SINKS = {"eval", "exec"}
DESER_SINKS = {"pickle.loads", "pickle.load", "_pickle.loads"}

SUPPRESSION_MARKERS = ("# faraday: ignore", "# noqa", "# nosec")


class TaintVisitor(ast.NodeVisitor):
    """
    AST Visitor implementing Intra-Procedural Data-Flow Taint Analysis.
    Tracks tainted variables originating from untrusted input sources and flags
    propagation into critical execution sinks.
    """

    def __init__(self, source_code: str, file_path: str, suppressed_rules: Optional[Set[str]] = None):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.file_path = file_path
        self.suppressed_rules = suppressed_rules or set()
        self.tainted_vars: Set[str] = set()
        self.var_sources: Dict[str, str] = {}
        self.findings: List[SecurityFinding] = []

    def _is_suppressed(self, line_no: int) -> bool:
        if 1 <= line_no <= len(self.source_lines):
            line_str = self.source_lines[line_no - 1]
            return any(marker in line_str for marker in SUPPRESSION_MARKERS)
        return False

    def _get_call_name(self, node: ast.Call) -> str:
        """Helper to extract fully qualified call name like 'os.system' or 'cursor.execute'."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            val_name = ""
            if isinstance(node.func.value, ast.Name):
                val_name = node.func.value.id
            elif isinstance(node.func.value, ast.Attribute):
                val_name = f"{getattr(node.func.value.value, 'id', '')}.{node.func.value.attr}"
            return f"{val_name}.{node.func.attr}".strip(".")
        return ""

    def _is_source(self, node: ast.AST) -> Optional[str]:
        """Check if an AST expression represents an untrusted source."""
        if isinstance(node, ast.Call):
            call_name = self._get_call_name(node).lower()
            if call_name in ("input", "os.getenv"):
                return call_name
        elif isinstance(node, ast.Attribute):
            attr_name = ""
            if isinstance(node.value, ast.Name):
                attr_name = f"{node.value.id}.{node.attr}".lower()
            elif isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
                attr_name = f"{node.value.value.id}.{node.value.attr}.{node.attr}".lower()
            for src in TAINT_SOURCES:
                if src in attr_name:
                    return attr_name
        elif isinstance(node, ast.Subscript):
            return self._is_source(node.value)
        return None

    def _is_tainted(self, node: ast.AST) -> Tuple[bool, str]:
        """Determine if an expression is tainted by an untrusted source."""
        # Direct source call
        src = self._is_source(node)
        if src:
            return True, src

        # Variable lookup
        if isinstance(node, ast.Name) and node.id in self.tainted_vars:
            return True, self.var_sources.get(node.id, node.id)

        # String binary operation (+, %)
        if isinstance(node, ast.BinOp):
            left_tainted, left_src = self._is_tainted(node.left)
            if left_tainted:
                return True, left_src
            right_tainted, right_src = self._is_tainted(node.right)
            if right_tainted:
                return True, right_src

        # Python JoinedStr (f-strings)
        if isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.FormattedValue):
                    part_tainted, part_src = self._is_tainted(part.value)
                    if part_tainted:
                        return True, part_src

        return False, ""

    def visit_Assign(self, node: ast.Assign):
        """Track variable assignments from sources or tainted expressions."""
        tainted, src_name = self._is_tainted(node.value)
        if tainted:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.tainted_vars.add(target.id)
                    self.var_sources[target.id] = src_name
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Analyze function calls acting as critical sinks."""
        call_name = self._get_call_name(node)
        call_lower = call_name.lower()
        line_no = getattr(node, "lineno", 1)

        if not self._is_suppressed(line_no):
            snippet = self.source_lines[line_no - 1].strip() if 1 <= line_no <= len(self.source_lines) else call_name

            # 1. SQL Injection Sink (CWE-89)
            if any(call_lower.endswith(s) for s in SQL_SINKS):
                if node.args:
                    arg0 = node.args[0]
                    # Direct concatenation or tainted variable in execute call
                    is_concat = isinstance(arg0, (ast.BinOp, ast.JoinedStr))
                    tainted, src_name = self._is_tainted(arg0)
                    if (is_concat or tainted) and "SEC-SQL01" not in self.suppressed_rules:
                        self.findings.append(
                            SecurityFinding.from_ast_taint(
                                rule_id="SEC-SQL01",
                                file_path=self.file_path,
                                line_number=line_no,
                                source_name=src_name or "string concatenation",
                                sink_name=call_name,
                                evidence=snippet
                            )
                        )

            # 2. Command Injection Sink (CWE-78)
            has_shell_true = any(
                isinstance(kw, ast.keyword) and kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in node.keywords
            )
            is_cmd_sink = call_lower in COMMAND_SINKS or (call_lower.startswith("subprocess.") and has_shell_true) or call_lower == "os.system"
            if is_cmd_sink and node.args and "SEC-CMD01" not in self.suppressed_rules:
                tainted, src_name = self._is_tainted(node.args[0])
                is_concat = isinstance(node.args[0], (ast.BinOp, ast.JoinedStr))
                if tainted or is_concat:
                    self.findings.append(
                        SecurityFinding.from_ast_taint(
                            rule_id="SEC-CMD01",
                            file_path=self.file_path,
                            line_number=line_no,
                            source_name=src_name or "dynamic shell variable",
                            sink_name=call_name,
                            evidence=snippet
                        )
                    )

            # 3. Dynamic Evaluation Sink (CWE-95)
            if call_lower in EVAL_SINKS and "SEC-EVAL01" not in self.suppressed_rules:
                if node.args:
                    tainted, src_name = self._is_tainted(node.args[0])
                    # Flag eval/exec unless argument is a hardcoded literal constant
                    if not isinstance(node.args[0], ast.Constant):
                        self.findings.append(
                            SecurityFinding.from_ast_taint(
                                rule_id="SEC-EVAL01",
                                file_path=self.file_path,
                                line_number=line_no,
                                source_name=src_name or "dynamic expression",
                                sink_name=call_name,
                                evidence=snippet
                            )
                        )

            # 4. Insecure Deserialization Sink (CWE-502)
            if any(call_lower.endswith(s) for s in DESER_SINKS) and "SEC-DESER01" not in self.suppressed_rules:
                self.findings.append(
                    SecurityFinding.from_ast_taint(
                        rule_id="SEC-DESER01",
                        file_path=self.file_path,
                        line_number=line_no,
                        source_name="untrusted serialized payload",
                        sink_name=call_name,
                        evidence=snippet
                    )
                )

        self.generic_visit(node)


def analyze_python_ast(source_code: str, file_path: str, suppressed_rules: Optional[Set[str]] = None) -> List[SecurityFinding]:
    """
    Parse Python source into AST and run data-flow taint analysis.
    Returns structured SecurityFinding instances for discovered flaws.
    """
    if not source_code or not source_code.strip():
        return []
    try:
        tree = ast.parse(source_code, filename=file_path)
    except SyntaxError:
        return []

    visitor = TaintVisitor(source_code, file_path, suppressed_rules=suppressed_rules)
    visitor.visit(tree)
    return visitor.findings
