"""
git_utils.py

Provides robust Git integration for enterprise projects:
- Detects repository root
- Retrieves list of staged files (`git diff --cached`) for instant pre-commit scans
- Retrieves list of changed files against target branch (`git diff <target>`) for PR/CI reviews
- Generates and installs self-contained pre-commit hooks
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def find_git_root(path: Path) -> Optional[Path]:
    """Find the root directory of the git repository enclosing path."""
    current = path.resolve()
    if current.is_file():
        current = current.parent

    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    return None


def run_git_command(args: List[str], cwd: Path) -> List[str]:
    """Run a git command and return stripped non-empty output lines."""
    git_bin = shutil.which("git")
    if not git_bin:
        return []

    try:
        proc = subprocess.run(
            [git_bin] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def get_staged_files(repo_root: Path) -> List[Path]:
    """Return absolute paths of all staged files (Added, Copied, Modified, Renamed)."""
    rel_files = run_git_command(["diff", "--cached", "--name-only", "--diff-filter=ACMR"], repo_root)
    valid_paths = []
    for rf in rel_files:
        p = repo_root / rf
        if p.exists() and p.is_file():
            valid_paths.append(p.resolve())
    return valid_paths


def get_diff_files(repo_root: Path, target_ref: str = "main") -> List[Path]:
    """Return absolute paths of all changed files against target git ref/branch."""
    rel_files = run_git_command(["diff", target_ref, "--name-only", "--diff-filter=ACMR"], repo_root)
    if not rel_files and target_ref == "main":
        # Fallback to master if main branch does not exist
        rel_files = run_git_command(["diff", "master", "--name-only", "--diff-filter=ACMR"], repo_root)

    valid_paths = []
    for rf in rel_files:
        p = repo_root / rf
        if p.exists() and p.is_file():
            valid_paths.append(p.resolve())
    return valid_paths


def install_pre_commit_hook(repo_root: Path) -> Path:
    """
    Install a high-speed pre-commit hook into .git/hooks/pre-commit.
    Scans only staged files to provide sub-second developer feedback.
    """
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        raise FileNotFoundError(f"No .git directory found at {repo_root}")

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"

    script = """#!/bin/sh
# Faraday Automatic On-Device Pre-Commit Gate
# Scans staged files for hardcoded credentials & critical code vulnerabilities.

echo "[Faraday] Running offline security and code assurance check on staged files..."

# Check if uv is present, else fallback to direct python / faraday
if command -v uv >/dev/null 2>&1; then
    uv run faraday --staged --fail-on HIGH
elif command -v faraday >/dev/null 2>&1; then
    faraday --staged --fail-on HIGH
elif command -v codeguard >/dev/null 2>&1; then
    codeguard --staged --fail-on HIGH
else
    python -m backend.cli --staged --fail-on HIGH
fi

STATUS=$?
if [ $STATUS -ne 0 ]; then
    echo "\\n[Faraday] COMMIT BLOCKED: High-severity security issues found in staged code."
    echo "[Faraday] Resolve the issues above or bypass with 'git commit --no-verify' if intentional.\\n"
    exit 1
fi

exit 0
"""
    hook_file.write_text(script, encoding="utf-8")
    try:
        # On POSIX / Git Bash, make executable
        import stat
        hook_file.chmod(hook_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass

    return hook_file
