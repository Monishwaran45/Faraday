"""Interactive scan-review-approve-rescan workflow for Faraday."""
from __future__ import annotations
from pathlib import Path
from typing import Callable, Any

from backend.core.file_scanner import scan_project
from backend.core.proof_of_fix import PatchError, apply_patch, propose_patch
from backend.core.secret_scanner import scan_all


def run_proof_of_fix(project_root: str | Path, relative_path: str, replacement_text: str, *, approve: Callable[[], bool], console: Any) -> int:
    """Scan a target, show findings and a proposed diff, ask for approval, then rescan."""
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise PatchError("Project root must be an existing directory.")
    proposal = propose_patch(root, relative_path, replacement_text)
    target = (root / relative_path).resolve()
    before_scan = scan_project(str(root), only_files=[str(target)])
    before_findings = scan_all(before_scan.chunks)
    if not before_findings:
        console.print(f"No findings detected in {relative_path}; no patch was applied.", style="yellow")
        return 2
    console.print(f"Findings in {relative_path}:", style="bold yellow")
    for finding in before_findings:
        console.print(f"- {finding.severity.upper()} {finding.rule_id} line {finding.line_number}: {finding.label}")
    console.print("\nProposed patch (review before approving):", style="bold cyan")
    console.print(proposal.diff, markup=False)
    if not approve():
        console.print("Patch declined; the target file was not changed.", style="yellow")
        return 1
    digest = apply_patch(root, proposal, approved=True)
    console.print(f"Patch applied. SHA-256: {digest}", style="green")
    after_scan = scan_project(str(root), only_files=[str(target)])
    after_findings = scan_all(after_scan.chunks)
    after_keys = {(f.rule_id, f.label) for f in after_findings}
    remaining = [f for f in before_findings if (f.rule_id, f.label) in after_keys]
    if remaining:
        console.print(f"Rescan complete: {len(remaining)} previously detected finding(s) remain. The patch is not verified as a fix.", style="bold yellow")
        for finding in remaining:
            console.print(f"- {finding.rule_id} line {finding.line_number}: {finding.label}")
    else:
        console.print("Rescan complete: original finding signatures were not reproduced. Run relevant tests and review the code; this is not a proof of security.", style="green")
    return 0
