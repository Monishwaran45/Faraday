"""Interactive CLI for Faraday's scan, review, approval, and rescan workflow."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from rich.console import Console
from rich.prompt import Confirm

from backend.core.proof_of_fix import PatchError
from backend.core.proof_of_fix_workflow import run_proof_of_fix


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="faraday-fix",
        description="Scan a file, review a proposed patch, require approval, and rescan.",
    )
    parser.add_argument("project_root", help="Root directory of the project to scan")
    parser.add_argument("target", help="Target file path relative to the project root")
    parser.add_argument(
        "--replacement-file",
        required=True,
        help="UTF-8 file containing the complete proposed replacement contents",
    )
    args = parser.parse_args()
    try:
        replacement_text = Path(args.replacement_file).resolve().read_text(encoding="utf-8")
        return run_proof_of_fix(
            args.project_root,
            args.target,
            replacement_text,
            approve=lambda: Confirm.ask("Apply this patch to the target file?", default=False),
            console=Console(),
        )
    except (OSError, UnicodeError, PatchError) as exc:
        Console(stderr=True).print(f"Proof-of-Fix aborted: {exc}", style="bold red")
        return 2


if __name__ == "__main__":
    sys.exit(main())
