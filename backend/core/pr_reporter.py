"""
pr_reporter.py

GitHub Actions Pull Request (PR) reporter for Faraday.
Generates:
1. Native GitHub Actions inline workflow annotations (::error and ::warning)
   which display directly on the modified diff lines in the GitHub PR Files Changed tab.
2. Structured Markdown PR summary comment for GitHub bot posting.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.core.finding import SecurityFinding


def format_github_workflow_annotation(finding: SecurityFinding, repo_root: Optional[Path] = None) -> str:
    """
    Formats finding as GitHub Actions workflow command annotation:
    ::error file={name},line={line},title={title}::{message}
    """
    level = "error" if finding.severity.upper() == "HIGH" else "warning"
    rel_path = finding.file_path
    if repo_root:
        try:
            rel_path = str(Path(finding.file_path).relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            pass

    title = f"[{finding.source}] {finding.rule_id} ({finding.cwe})"
    # Escape newlines for GitHub workflow command syntax
    msg = finding.explanation.replace("\n", "%0A").replace("\r", "%0D")
    return f"::{level} file={rel_path},line={finding.line_number},title={title}::{msg}"


def emit_pr_annotations(findings: List[SecurityFinding], repo_root: Optional[Path] = None) -> List[str]:
    """Prints GitHub workflow command annotations to stdout for GitHub Actions runners."""
    annotations = []
    for f in findings:
        ann = format_github_workflow_annotation(f, repo_root=repo_root)
        annotations.append(ann)
        print(ann)
    return annotations


def generate_pr_markdown_summary(
    findings: List[SecurityFinding],
    elapsed_seconds: float = 0.0,
    commit_sha: Optional[str] = None
) -> str:
    """
    Builds a structured, rich Markdown summary for posting as a GitHub PR comment.
    """
    high_count = sum(1 for f in findings if f.severity.upper() == "HIGH")
    med_count = sum(1 for f in findings if f.severity.upper() == "MEDIUM")
    low_count = sum(1 for f in findings if f.severity.upper() == "LOW")
    total = len(findings)

    status_badge = "FAILED" if high_count > 0 else "PASSED"
    badge_color = "red" if high_count > 0 else "green"

    md = []
    md.append("##  Faraday On-Device Security Audit Summary")
    md.append(f"**Status:** `[{status_badge}]` &nbsp;|&nbsp; **High:** `{high_count}` &nbsp;|&nbsp; **Medium:** `{med_count}` &nbsp;|&nbsp; **Low:** `{low_count}` &nbsp;|&nbsp; **Scan Time:** `{elapsed_seconds:.2f}s`")
    if commit_sha:
        md.append(f"**Target Commit:** `{commit_sha[:8]}`")
    md.append("")

    if total == 0:
        md.append("> **Zero Security Vulnerabilities Detected.** This pull request meets all Faraday quality & compliance gates.")
        return "\n".join(md)

    md.append("| Severity | Source | Rule & CWE | Location | Confidence | Evidence & Remediation |")
    md.append("| :---: | :---: | :--- | :--- | :---: | :--- |")

    for f in findings:
        sev_icon = " " if f.severity.upper() == "HIGH" else (" " if f.severity.upper() == "MEDIUM" else " ")
        loc = f"`{Path(f.file_path).name}:{f.line_number}`"
        conf = f"{int(f.confidence * 100)}%"
        remed = f.remediation.replace("\n", " ") if f.remediation else "Review and sanitize input."
        md.append(f"| {sev_icon} **{f.severity}** | `{f.source}` | **{f.rule_id}**<br/>`{f.cwe}` | {loc} | {conf} | `{f.evidence[:40]}`<br/>*{remed[:80]}* |")

    md.append("")
    md.append("---")
    md.append("*Audited locally by Faraday — 100% Air-Gapped Zero-Egress Silicon Engine on Qualcomm Snapdragon Hexagon NPU.*")
    return "\n".join(md)
