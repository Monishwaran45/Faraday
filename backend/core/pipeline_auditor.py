"""
pipeline_auditor.py

CI/CD Build Pipeline & AI Agent Permission Auditor.
Audits GitHub Actions workflows, Dockerfiles, and AI Agent configuration files
for supply-chain risks, remote execution vectors (curl | bash), unpinned actions,
excessive token permissions (write-all), and unrestricted AI agent execution privileges.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich import box


@dataclass
class PipelineFinding:
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    rule_id: str
    target_type: str  # 'github_actions', 'dockerfile', 'ai_agent'
    file_path: str
    line_number: int
    code_snippet: str
    message: str
    remediation: str


@dataclass
class PipelineAuditReport:
    target_path: str
    files_scanned: int
    findings: List[PipelineFinding] = field(default_factory=list)

    @property
    def has_findings(self) -> bool:
        return len(self.findings) > 0

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity.upper() == "HIGH")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity.upper() == "MEDIUM")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity.upper() == "LOW")


def audit_github_workflow_file(file_path: Path) -> List[PipelineFinding]:
    """Audit a single GitHub Actions workflow YAML file for security flaws."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    lines = content.splitlines()

    # Rule 1: Remote script execution (curl | bash / wget | sh)
    curl_pipe_pattern = re.compile(r"""(curl\s+.*?\|\s*(bash|sh)|wget\s+.*?\|\s*(bash|sh))""", re.IGNORECASE)
    for idx, line in enumerate(lines, 1):
        if curl_pipe_pattern.search(line):
            findings.append(
                PipelineFinding(
                    severity="HIGH",
                    rule_id="PIPE-SEC-001",
                    target_type="github_actions",
                    file_path=str(file_path),
                    line_number=idx,
                    code_snippet=line.strip(),
                    message="Piping untrusted remote scripts directly into bash/sh creates remote code execution risks.",
                    remediation="Download the script, verify its SHA-256 integrity hash, and execute from disk with minimal permissions.",
                )
            )

    # Rule 2: Dangerous pull_request_target with head.sha checkout
    if "pull_request_target:" in content or "pull_request_target" in content:
        for idx, line in enumerate(lines, 1):
            if "github.event.pull_request.head.sha" in line or "ref: ${{ github.event.pull_request.head.sha }}" in line:
                findings.append(
                    PipelineFinding(
                        severity="HIGH",
                        rule_id="PIPE-SEC-002",
                        target_type="github_actions",
                        file_path=str(file_path),
                        line_number=idx,
                        code_snippet=line.strip(),
                        message="Combining 'pull_request_target' with untrusted PR checkout allows external attackers to steal secrets (PwnRequest).",
                        remediation="Use standard 'pull_request' trigger for untrusted forks, or do not checkout untrusted PR code in privileged workflows.",
                    )
                )

    # Rule 3: Overly permissive permissions (write-all)
    for idx, line in enumerate(lines, 1):
        if re.search(r"^\s*permissions:\s*write-all\b", line, re.IGNORECASE):
            findings.append(
                PipelineFinding(
                    severity="HIGH",
                    rule_id="PIPE-SEC-003",
                    target_type="github_actions",
                    file_path=str(file_path),
                    line_number=idx,
                    code_snippet=line.strip(),
                    message="Workflow specifies 'permissions: write-all', granting broad repository write access to the GITHUB_TOKEN.",
                    remediation="Define minimal granular permissions per job (e.g. `contents: read`, `pull-requests: write`).",
                )
            )

    # Rule 4: Unpinned third-party action (@master, @main, @latest)
    unpinned_action_pattern = re.compile(r"""uses:\s*([\w\-]+/[\w\-]+)@(master|main|latest)\b""", re.IGNORECASE)
    for idx, line in enumerate(lines, 1):
        m = unpinned_action_pattern.search(line)
        if m:
            action_name = m.group(1)
            findings.append(
                PipelineFinding(
                    severity="MEDIUM",
                    rule_id="PIPE-SEC-004",
                    target_type="github_actions",
                    file_path=str(file_path),
                    line_number=idx,
                    code_snippet=line.strip(),
                    message=f"Action '{action_name}' is pinned to a mutable branch ({m.group(2)}), vulnerable to upstream supply-chain poisoning.",
                    remediation=f"Pin third-party action to an immutable 40-character commit SHA (e.g. `uses: {action_name}@<commit-sha>`).",
                )
            )

    return findings


def audit_dockerfile(file_path: Path) -> List[PipelineFinding]:
    """Audit a Dockerfile for container security and least-privilege principles."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    lines = content.splitlines()
    has_user_directive = False

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("USER ") and not stripped.endswith("root"):
            has_user_directive = True

        # Rule: Hardcoded secrets in ENV
        if re.search(r"^\s*ENV\s+.*?(SECRET|PASSWORD|TOKEN|KEY|PRIVATE)\s*=", line, re.IGNORECASE):
            findings.append(
                PipelineFinding(
                    severity="HIGH",
                    rule_id="DOCKER-SEC-001",
                    target_type="dockerfile",
                    file_path=str(file_path),
                    line_number=idx,
                    code_snippet=stripped,
                    message="Hardcoding secrets in Dockerfile ENV instructions persists credentials into immutable image layers.",
                    remediation="Inject secrets at container runtime using environment variables or Docker build secrets (`--secret`).",
                )
            )

        # Rule: Latest tag
        if re.search(r"^\s*FROM\s+[\w\-\.\/]+:latest\b", line, re.IGNORECASE):
            findings.append(
                PipelineFinding(
                    severity="LOW",
                    rule_id="DOCKER-SEC-002",
                    target_type="dockerfile",
                    file_path=str(file_path),
                    line_number=idx,
                    code_snippet=stripped,
                    message="Using ':latest' tag creates non-reproducible builds vulnerable to unexpected upstream breaking changes.",
                    remediation="Pin base image to a specific immutable semantic version or digest SHA (`@sha256:...`).",
                )
            )

    if not has_user_directive and any(l.strip().startswith("CMD ") or l.strip().startswith("ENTRYPOINT ") for l in lines):
        findings.append(
            PipelineFinding(
                severity="MEDIUM",
                rule_id="DOCKER-SEC-003",
                target_type="dockerfile",
                file_path=str(file_path),
                line_number=len(lines),
                code_snippet="USER root (Implicit)",
                message="Container executes as default 'root' user without a non-privileged USER declaration.",
                remediation="Create and declare a non-root user (e.g., `RUN useradd -u 1001 appuser && USER appuser`).",
            )
        )

    return findings


def audit_ai_agent_config(file_path: Path) -> List[PipelineFinding]:
    """Audit AI coding agent configuration files for over-permissive execution rights."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    lines = content.splitlines()

    # Look for unrestricted bash/shell execution permissions in JSON/YAML agent configs
    unrestricted_shell_pattern = re.compile(r"""("execute_commands"|"auto_run"|"allow_terminal"|"run_shell"|"autoRun")\s*:\s*(true|"true"|"always"|"unrestricted")""", re.IGNORECASE)
    for idx, line in enumerate(lines, 1):
        if unrestricted_shell_pattern.search(line):
            findings.append(
                PipelineFinding(
                    severity="HIGH",
                    rule_id="AGENT-SEC-001",
                    target_type="ai_agent",
                    file_path=str(file_path),
                    line_number=idx,
                    code_snippet=line.strip(),
                    message="AI Agent is configured with unrestricted autonomous shell execution without human confirmation.",
                    remediation="Enforce interactive confirmation prompts or restrict commands to a safe deterministic allowlist.",
                )
            )

    # Look for broad filesystem permissions
    if re.search(r"""("allowed_directories"|"workspace_paths"|"read_paths")\s*:\s*\[\s*"/"\s*\]""", content):
        for idx, line in enumerate(lines, 1):
            if '"/"' in line:
                findings.append(
                    PipelineFinding(
                        severity="HIGH",
                        rule_id="AGENT-SEC-002",
                        target_type="ai_agent",
                        file_path=str(file_path),
                        line_number=idx,
                        code_snippet=line.strip(),
                        message="AI Agent granted read/write access to root filesystem ('/'), bypassing project boundaries.",
                        remediation="Confine AI agent filesystem boundaries strictly to the local workspace directory.",
                    )
                )

    return findings


def audit_codebase_pipelines(target_path: Path) -> PipelineAuditReport:
    """Audits target codebase for CI/CD workflows, Dockerfiles, and AI Agent configs."""
    target_path = target_path.resolve()
    report = PipelineAuditReport(target_path=str(target_path), files_scanned=0)

    # 1. GitHub Workflows
    workflow_files = []
    if target_path.is_file() and target_path.suffix in (".yml", ".yaml"):
        workflow_files = [target_path]
    elif (target_path / ".github" / "workflows").exists():
        workflow_files = list((target_path / ".github" / "workflows").glob("*.yml")) + list((target_path / ".github" / "workflows").glob("*.yaml"))

    for wf in workflow_files:
        report.files_scanned += 1
        report.findings.extend(audit_github_workflow_file(wf))

    # 2. Dockerfiles
    docker_files = []
    if target_path.is_file() and "dockerfile" in target_path.name.lower():
        docker_files = [target_path]
    elif target_path.is_dir():
        docker_files = [p for p in target_path.glob("*Dockerfile*") if p.is_file()]

    for df in docker_files:
        report.files_scanned += 1
        report.findings.extend(audit_dockerfile(df))

    # 3. AI Agent Configs
    agent_patterns = [".cursorrules", "*agent*.json", ".mcp*.json", "agent_config.json"]
    agent_files = []
    if target_path.is_file() and any(k in target_path.name.lower() for k in ("agent", "cursorrules", "mcp")):
        agent_files = [target_path]
    elif target_path.is_dir():
        for pat in agent_patterns:
            agent_files.extend(list(target_path.glob(pat)))

    for af in set(agent_files):
        report.files_scanned += 1
        report.findings.extend(audit_ai_agent_config(af))

    return report


def print_pipeline_audit_report(report: PipelineAuditReport, console: Optional[Console] = None):
    """Renders a rich terminal summary of the CI/CD and AI Agent permission audit."""
    if console is None:
        console = Console()

    table = Table(
        title="[bold yellow]🛡️ CI/CD Build Pipeline & AI Agent Permission Audit[/]",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="yellow",
        expand=False,
    )
    table.add_column("Severity", justify="center", width=12)
    table.add_column("Rule ID", style="bold cyan", width=16)
    table.add_column("Location", style="white", width=28)
    table.add_column("Security Risk & Hardening Fix", style="white")

    if report.files_scanned == 0:
        console.print()
        console.print("[bold yellow][!] No CI/CD workflows, Dockerfiles, or AI Agent configs found in target path.[/]\n")
        return

    if not report.findings:
        console.print()
        console.print("[bold green][✓] All CI/CD Pipelines & Agent Configurations Verified Secure![/]")
        console.print(f"[dim]Scanned {report.files_scanned} pipeline/agent config file(s). Zero supply-chain or privilege escalation risks found.[/]\n")
        return

    for f in report.findings:
        if f.severity.upper() == "HIGH":
            sev_badge = "[bold white on red] HIGH [/]"
        elif f.severity.upper() == "MEDIUM":
            sev_badge = "[bold black on yellow] MEDIUM [/]"
        else:
            sev_badge = "[bold white on blue] LOW [/]"

        loc = f"{Path(f.file_path).name}:{f.line_number}"
        detail = f"[bold red]{f.message}[/]\n[dim]Code:[/] `{f.code_snippet}`\n[bold green]Hardening:[/] {f.remediation}"
        table.add_row(sev_badge, f.rule_id, loc, detail)

    console.print()
    console.print(table)
    console.print()
    console.print(
        f"[bold]Pipeline Summary:[/] Scanned [cyan]{report.files_scanned}[/] file(s) ➔ "
        f"[bold red]{report.high_count} High[/], [bold yellow]{report.medium_count} Medium[/], [bold blue]{report.low_count} Low[/] security risk(s) identified.\n"
    )
