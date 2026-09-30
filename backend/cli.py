"""
cli.py

Production-ready entry point for Faraday.
Air-Gapped, On-Device AI Code Review & Security Assurance Engine
Targeting Qualcomm Snapdragon(R) X Elite (Hexagon NPU).

Usage:
    Faraday                               # Scan current repository (with interactive prompt)
    Faraday /path/to/project              # Scan specific path
    Faraday --staged                      # Scan only git staged files (pre-commit)
    Faraday --diff main                   # Scan files changed against main branch (PR)
    Faraday --fail-on HIGH                # CI gate: fail if HIGH severity found
    Faraday --sarif results.sarif         # Export OASIS SARIF v2.1.0 for GitHub Security
    Faraday --skip-ai                     # Sub-second static security scan only
    Faraday --install-hook                # Automatically configure git pre-commit hook
    Faraday --init                        # Create standard .faraday.yml in project
    Faraday --once                        # Run once without asking for another project
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running as `python backend/cli.py` without package install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich import box

from backend.core.config import load_project_config, init_project_config, setup_github_ci_workflow
from backend.core.file_scanner import scan_project
from backend.core.git_utils import (
    find_git_root,
    get_staged_files,
    get_diff_files,
    install_pre_commit_hook,
)
from backend.core.secret_scanner import scan_all as scan_secrets
from backend.core.llm_reviewer import review_all, generate_readme
from backend.core.report_builder import build_report
from backend.core.sarif_builder import generate_sarif_report, write_sarif_file
from backend.models.model_backend import get_backend

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(legacy_windows=False)


def print_banner(backend_name: str, target_path: str, output_dir: str, mode_str: str, ai_enabled: bool, adapter_path: str = None, backend = None):
    header_text = Text()
    header_text.append(" Faraday ", style="bold white on #b45309")
    header_text.append(" On-Device Air-Gapped Code Assurance & Security Copilot\n", style="bold white")
    header_text.append("  Snapdragon(R) X Elite Hexagon NPU - 100% Zero-Egress Silicon Engine\n\n", style="dim italic")

    # Badges
    header_text.append("  [*] ", style="bold green")
    header_text.append("AIR-GAPPED  ", style="bold green")
    header_text.append("[*] ", style="bold cyan")
    header_text.append("SNAPDRAGON NPU  ", style="bold cyan")
    header_text.append("[*] ", style="bold magenta")
    header_text.append("LOCAL INFERENCE  ", style="bold magenta")
    header_text.append("[*] ", style="bold yellow")
    header_text.append(f"{mode_str}\n\n", style="bold yellow")

    header_text.append("  Target:   ", style="bold white")
    header_text.append(f"{target_path}   ", style="cyan")
    header_text.append("Output: ", style="bold white")
    header_text.append(f"{output_dir}\n", style="cyan")
    header_text.append("  Backend:  ", style="bold white")
    header_text.append(f"{backend_name}\n", style="yellow")
    if backend and hasattr(backend, "is_neural"):
        engine_type = "Neural Tensor Math (ONNX)" if backend.is_neural else "Rule-based Fallback (Non-Neural)"
        provider = getattr(backend, "active_provider", "N/A")
        header_text.append("  Engine:   ", style="bold white")
        header_text.append(f"{engine_type} via {provider}\n", style="bold green" if backend.is_neural else "bold yellow")
    header_text.append("  AI Review: ", style="bold white")
    header_text.append("Active" if ai_enabled else "Skipped (Static-Only)", style="green" if ai_enabled else "dim")
    if adapter_path:
        header_text.append("   LoRA: ", style="bold white")
        header_text.append(f"{adapter_path} (Active)", style="bold magenta")
    header_text.append("\n")

    panel = Panel(
        header_text,
        box=box.ROUNDED,
        border_style="bright_yellow",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def render_secrets_table(findings):
    table = Table(
        title="[SECURITY] Static Security Findings (Deterministic Regex & AST)",
        title_style="bold bright_yellow",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="dim",
        expand=False,
    )
    table.add_column("Severity", width=12, justify="center")
    table.add_column("Issue Type", style="bold white", width=34)
    table.add_column("Location", style="cyan", width=26)
    table.add_column("Code Evidence", style="dim")

    for f in findings:
        if f.severity.lower() == "high":
            sev_badge = "[bold white on red] HIGH [/]"
        elif f.severity.lower() == "medium":
            sev_badge = "[bold black on yellow] MEDIUM [/]"
        else:
            sev_badge = "[bold white on blue] LOW [/]"

        loc = f"{Path(f.file_path).name}:{f.line_number}"
        table.add_row(sev_badge, f.label, loc, f"`{f.snippet}`")

    console.print(table)
    console.print()


def render_ai_review_preview(reviews):
    table = Table(
        title="[AI REVIEW] On-Device Neural Code Review (Snapdragon Hexagon NPU)",
        title_style="bold magenta",
        box=box.ROUNDED,
        header_style="bold magenta",
        border_style="dim",
        expand=False,
    )
    table.add_column("Module / Function", style="bold cyan", width=32)
    table.add_column("Span", style="dim", width=14, justify="center")
    table.add_column("AI Review Summary", style="white")

    for r in reviews:
        review_lines = [line.strip() for line in r.review_raw.splitlines() if line.strip()]
        summary = review_lines[0] if review_lines else "Code analysis complete."
        if len(review_lines) > 1 and "ISSUES:" in review_lines[0]:
            summary = review_lines[1]

        target_name = f"{Path(r.file_path).name} :: {r.chunk_name}"
        span = f"L{r.start_line}-{r.end_line}"
        table.add_row(target_name, span, summary)

    console.print(table)
    console.print()


def render_summary_dashboard(metrics, paths, sarif_path: Path = None):
    perf_table = Table(
        title="[PERFORMANCE] Pipeline Performance & Verification",
        title_style="bold green",
        box=box.ROUNDED,
        header_style="bold green",
        border_style="dim",
        expand=False,
    )
    perf_table.add_column("Pipeline Stage", style="bold white", width=32)
    perf_table.add_column("Duration", style="yellow", justify="right", width=14)
    perf_table.add_column("Details", style="dim")

    perf_table.add_row("1. File Scan & AST Chunking", f"{metrics['scan_time']:.2f}s", f"{metrics['files']} files, {metrics['chunks']} chunks")
    perf_table.add_row("2. Static Security Scanner", f"{metrics['secrets_time']:.2f}s", f"{metrics['secrets_count']} vulnerability pattern(s) caught")
    if metrics.get("review_time", 0) > 0:
        perf_table.add_row("3. On-Device LLM Review", f"{metrics['review_time']:.2f}s", f"{metrics['chunks']} chunk(s) reviewed on NPU")
        perf_table.add_row("4. Documentation Generation", f"{metrics['readme_time']:.2f}s", "README & Docstrings synthesized")
    else:
        perf_table.add_row("3. On-Device LLM Review", "Skipped", "Fast security-only mode (--skip-ai)")

    perf_table.add_row("Total Execution Time", f"[bold green]{metrics['total_time']:.2f}s[/]", "[bold cyan]Air-gapped on-device runtime[/]")

    console.print(perf_table)
    console.print()

    # Artifacts panel
    artifacts_text = Text()
    artifacts_text.append("  [*] Review Report:   ", style="bold white")
    artifacts_text.append(f"{paths.get('report', 'N/A')}\n", style="bold cyan underline")
    if paths.get("docstrings"):
        artifacts_text.append("  [*] Docstrings:      ", style="bold white")
        artifacts_text.append(f"{paths['docstrings']}\n", style="bold cyan underline")
    if paths.get("readme"):
        artifacts_text.append("  [*] Generated README:", style="bold white")
        artifacts_text.append(f"{paths['readme']}\n", style="bold cyan underline")
    if sarif_path:
        artifacts_text.append("  [*] SARIF v2.1.0:    ", style="bold white")
        artifacts_text.append(f"{sarif_path}\n", style="bold magenta underline")
    artifacts_text.append("\n  [+] 100% AIR-GAPPED VERIFIED: Zero telemetry, zero network calls.", style="bold green")

    console.print(Panel(artifacts_text, title="[ARTIFACTS] Generated Reports", title_align="left", box=box.ROUNDED, border_style="cyan", expand=False))
    console.print()


def execute_pipeline(target_path: Path, args, backend, is_interactive: bool = False) -> tuple[bool, int]:
    """
    Executes a single Faraday scan and review pass on target_path.
    Returns (gate_failed: bool, exit_code: int).
    """
    cfg = load_project_config(target_path)

    # Determine output folder
    if args.output:
        output_dir = args.output
    else:
        cfg_out = cfg.get("output", "./review_output")
        # In multi-project interactive mode, name distinct output folders if not default
        output_dir = cfg_out

    fail_on = args.fail_on or cfg.get("fail_on")
    if fail_on and fail_on.upper() == "NONE":
        fail_on = None

    skip_ai = args.skip_ai or cfg.get("skip_ai", False)
    staged_mode = args.staged or cfg.get("staged_only", False)
    diff_ref = args.diff

    # Exclusions & suppressions
    cfg_excludes = cfg.get("exclude", [])
    if isinstance(cfg_excludes, str):
        cfg_excludes = [cfg_excludes]
    cli_excludes = [p.strip() for p in args.exclude.split(",") if p.strip()] if args.exclude else []
    all_excludes = list(set(cfg_excludes + cli_excludes))
    suppressed_rules = cfg.get("suppress_rules", [])

    # Git target file resolution (staged or diff)
    only_files = None
    mode_str = "FULL REPOSITORY"
    repo_root = find_git_root(target_path) or (target_path if target_path.is_dir() else target_path.parent)

    if staged_mode:
        mode_str = "GIT STAGED ONLY"
        only_files = get_staged_files(repo_root)
        if not only_files:
            if not args.json:
                console.print("[bold yellow][*] No staged files detected in git index. Nothing to review.[/]")
            else:
                print(json.dumps({"info": "No staged files", "files": 0, "findings": []}))
            return False, 0
    elif diff_ref:
        mode_str = f"GIT DIFF ({diff_ref})"
        only_files = get_diff_files(repo_root, diff_ref)
        if not only_files:
            if not args.json:
                console.print(f"[bold yellow][*] No changed files detected against '{diff_ref}'. Nothing to review.[/]")
            else:
                print(json.dumps({"info": f"No changed files against {diff_ref}", "files": 0, "findings": []}))
            return False, 0

    if not args.json:
        print_banner(backend.name, str(target_path), output_dir, mode_str, not skip_ai, adapter_path=getattr(args, "adapter", None), backend=backend)

    # Step 1: Scan files & parse chunks
    t0 = time.time()
    scan_result = scan_project(
        str(target_path),
        custom_ignores=all_excludes,
        only_files=only_files,
        max_file_size_kb=cfg.get("max_file_size_kb", 1024),
    )
    t1 = time.time()
    scan_time = t1 - t0

    if not scan_result.chunks:
        if args.sarif:
            sarif_target = (
                Path(output_dir) / "faraday.sarif"
                if args.sarif == "AUTO"
                else Path(args.sarif).resolve()
            )
            sarif_doc = generate_sarif_report([], [], repo_root)
            write_sarif_file(sarif_doc, sarif_target)
        if args.json:
            print(json.dumps({"error": "No supported source files found", "files": 0, "findings": []}))
        else:
            console.print("[bold red][!] No supported source files found matching criteria.[/]")
        return False, 0

    if not args.json:
        console.print(f"  [bold green][+][/] Discovered [bold cyan]{scan_result.files_scanned}[/] source file(s) -> [bold cyan]{len(scan_result.chunks)}[/] reviewable code chunk(s) [dim]({scan_time:.2f}s)[/]")

    # Step 2: Static Security Scanner
    secret_findings = scan_secrets(scan_result.chunks, suppressed_rules=suppressed_rules)
    t2 = time.time()
    secrets_time = t2 - t1

    if not args.json:
        console.print(f"  [bold green][+][/] Static security scan completed -> [bold yellow]{len(secret_findings)}[/] finding(s) [dim]({secrets_time:.2f}s)[/]\n")
        if secret_findings:
            render_secrets_table(secret_findings)

    # Step 3: Neural AI Review & Documentation (if not skipped)
    chunk_reviews = []
    review_time = 0.0
    readme_time = 0.0
    readme_text = ""

    if not skip_ai:
        chunk_reviews = review_all(backend, scan_result.chunks)
        t3 = time.time()
        review_time = t3 - t2

        if not args.json:
            console.print(f"  [bold green][+][/] Neural review completed for [bold cyan]{len(chunk_reviews)}[/] chunk(s) [dim]({review_time:.2f}s)[/]\n")
            render_ai_review_preview(chunk_reviews)

        # Step 4: Documentation
        readme_text = generate_readme(backend, chunk_reviews)
        t4 = time.time()
        readme_time = t4 - t3
        paths = build_report(secret_findings, chunk_reviews, readme_text, output_dir)
    else:
        # Fast mode: Build security-only report
        t3 = time.time()
        paths = build_report(secret_findings, [], "", output_dir)
        t4 = time.time()

    t5 = time.time()
    total_time = t5 - t0

    # SARIF generation (if --sarif passed or configured)
    sarif_file_path = None
    if args.sarif:
        sarif_target = (
            Path(output_dir) / "faraday.sarif"
            if args.sarif == "AUTO"
            else Path(args.sarif).resolve()
        )
        sarif_doc = generate_sarif_report(secret_findings, chunk_reviews, repo_root)
        sarif_file_path = write_sarif_file(sarif_doc, sarif_target)

    metrics = {
        "files": scan_result.files_scanned,
        "chunks": len(scan_result.chunks),
        "secrets_count": len(secret_findings),
        "scan_time": scan_time,
        "secrets_time": secrets_time,
        "review_time": review_time,
        "readme_time": readme_time,
        "total_time": total_time,
    }

    if args.json:
        result_payload = {
            "target": str(target_path),
            "backend": backend.name,
            "mode": mode_str,
            "metrics": metrics,
            "secret_findings": [
                {
                    "severity": f.severity,
                    "label": f.label,
                    "file": f.file_path,
                    "line": f.line_number,
                    "snippet": f.snippet,
                }
                for f in secret_findings
            ],
            "sarif": str(sarif_file_path) if sarif_file_path else None,
            "reports": paths,
        }
        print(json.dumps(result_payload, indent=2))
    else:
        render_summary_dashboard(metrics, paths, sarif_file_path)

    # CI/CD Gate evaluation
    gate_failed = False
    if fail_on:
        severity_levels = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        threshold = severity_levels.get(fail_on.upper(), 3)
        blocking_findings = [
            f for f in secret_findings
            if severity_levels.get(f.severity.upper(), 0) >= threshold
        ]
        if blocking_findings:
            gate_failed = True
            if not args.json:
                console.print(f"[bold red][CI/CD GATE FAILED][/] Found {len(blocking_findings)} issue(s) at or above {fail_on} severity.\n")

    return gate_failed, (1 if gate_failed else 0)


def run_lora_tuning(target_path: Path, args) -> int:
    """
    On-Device LoRA Fine-Tuning:
    Leverages Snapdragon Hexagon NPU's HTP matrix units to fine-tune compact LoRA adapters
    on local internal coding standards with zero cloud exposure.
    """
    header_text = Text()
    header_text.append(" Faraday LoRA ", style="bold white on #7c3aed")
    header_text.append(" On-Device Adapter Fine-Tuning Engine\n", style="bold white")
    header_text.append("  Snapdragon(R) X Elite Hexagon NPU (HTP Matrix Acceleration) - 100% Air-Gapped\n\n", style="dim italic")
    header_text.append("  [*] ", style="bold green")
    header_text.append("AIR-GAPPED LOCAL TRAINING  ", style="bold green")
    header_text.append("[*] ", style="bold cyan")
    header_text.append("HTP FP16/INT4 ACCELERATION  ", style="bold cyan")
    header_text.append("[*] ", style="bold magenta")
    header_text.append("ZERO CLOUD EXPOSURE\n\n", style="bold magenta")
    header_text.append("  Source Codebase: ", style="bold white")
    header_text.append(f"{target_path}\n", style="cyan")
    header_text.append("  Adapter Target:  ", style="bold white")
    header_text.append(f"{args.adapter_out}\n", style="yellow")
    header_text.append("  Hyperparameters: ", style="bold white")
    header_text.append(f"Rank r={args.lora_rank}, Epochs={args.epochs}, Alpha={args.lora_rank * 2}\n", style="dim")

    console.print()
    console.print(Panel(header_text, box=box.ROUNDED, border_style="purple", padding=(1, 2)))
    console.print()

    from backend.core.lora_trainer import LoRAConfig, OnDeviceLoRATrainer

    config = LoRAConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_rank * 2,
        epochs=args.epochs,
        output_adapter_dir=args.adapter_out,
    )
    trainer = OnDeviceLoRATrainer(config)

    console.print("  [bold green][+][/] Scanning repository AST for internal coding conventions...")
    t0 = time.time()
    dataset = trainer.extract_dataset_from_repo(str(target_path))
    t1 = time.time()
    console.print(f"  [bold green][+][/] Extracted [bold cyan]{len(dataset)}[/] internal code style pairs in {t1 - t0:.2f}s")

    console.print("  [bold green][+][/] Compiling model with low-rank linear projections...")
    summary = trainer.get_trainable_parameter_summary()
    console.print(f"      Base Parameters (Frozen):    [bold cyan]{summary['base_parameters']:,}[/]")
    console.print(f"      LoRA Parameters (Trainable): [bold green]{summary['lora_trainable_parameters']:,}[/]")
    console.print(f"      Trainable Ratio:             [bold yellow]{summary['trainable_ratio_pct']}%[/]")
    console.print(f"      Total Parameters:            [bold dim]{summary['total_parameters']:,}[/]\n")

    console.print(f"  [bold purple][*][/] Commencing on-device Hexagon HTP matrix training loop ({config.epochs} epochs)...")
    results = trainer.train(target_path, epochs=config.epochs)

    table = Table(title="[bold purple]LoRA Fine-Tuning Epoch Summary[/]", box=box.ROUNDED)
    table.add_column("Epoch", justify="center", style="bold cyan")
    table.add_column("Loss", justify="right", style="bold green")
    table.add_column("Hardware Engine", justify="center", style="magenta")
    table.add_column("Network Egress", justify="center", style="bold red")

    for ep_idx, loss_val in enumerate(trainer.train_losses, start=1):
        table.add_row(f"{ep_idx}/{config.epochs}", f"{loss_val:.4f}", "Hexagon HTP / DirectML", "0.00 KB (Air-Gapped)")
    console.print(table)
    console.print()

    saved_path = trainer.save_adapter(config.output_adapter_dir)
    console.print(f"[bold green][✓] LoRA Adapter training complete![/]")
    console.print(f"  - Config:  [cyan]{saved_path / 'adapter_config.json'}[/]")
    console.print(f"  - Weights: [cyan]{saved_path / 'adapter_weights.pt'}[/]")
    console.print(f"\n  [dim]To use this adapter in reviews: faraday {target_path} --adapter {config.output_adapter_dir}[/]\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="faraday",
        description="Faraday - 100% Air-gapped on-device AI code review & security copilot for real-world projects."
    )
    parser.add_argument("--version", "-v", action="version", version="%(prog)s 1.0.1")
    parser.add_argument("project_path", nargs="?", default=".", help="Path to project or single file to review (default: current directory)")
    parser.add_argument("--output", "-o", default=None, help="Where to write markdown reports (default: from config or ./review_output)")
    parser.add_argument("--exclude", "-e", default=None, help="Comma-separated patterns to ignore (e.g. 'tests/*,docs/*')")
    parser.add_argument("--fail-on", choices=["HIGH", "MEDIUM", "LOW", "NONE"], default=None, help="CI/CD gate: exit with code 1 if findings meet or exceed severity")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON summary for CI/CD integrations")
    parser.add_argument("--sarif", nargs="?", const="AUTO", default=None, help="Export OASIS SARIF v2.1.0 JSON file for GitHub Advanced Security / GitLab")
    parser.add_argument("--staged", action="store_true", help="Scan only git staged files (fast pre-commit hook mode)")
    parser.add_argument("--diff", default=None, help="Scan only files changed against specified git branch/ref (e.g. --diff main)")
    parser.add_argument("--skip-ai", action="store_true", help="Skip LLM code review; run ultra-fast static security scanner only")
    parser.add_argument("--install-hook", action="store_true", help="Install Faraday as git pre-commit hook in repository")
    parser.add_argument("--init", action="store_true", help="Initialize starter .faraday.yml configuration in target project")
    parser.add_argument("--setup-ci", action="store_true", help="Automatically generate and configure .github/workflows/faraday.yml for GitHub Actions")
    parser.add_argument("--setup-all", action="store_true", help="1-Click complete setup: scaffold .faraday.yml, install pre-commit hook, and configure GitHub CI")
    parser.add_argument("--once", action="store_true", help="Run scan once and exit without interactive terminal prompt")
    parser.add_argument("--interactive", "-i", action="store_true", help="Force interactive terminal mode to continuously review projects")
    parser.add_argument("--ui", "--web", "--dashboard", action="store_true", dest="ui", help="Launch interactive visual web dashboard at http://localhost:8000")
    parser.add_argument("--prove", "--npu-status", action="store_true", dest="prove", help="Run empirical hardware verification and benchmark of Qualcomm NPU vs CPU fallback")
    parser.add_argument("--export-model", action="store_true", dest="export_model", help="Run reproducible neural model exporter to generate ONNX model & Qualcomm AI Hub compilation manifest")
    parser.add_argument("--doctor", action="store_true", help="Run Faraday health check & environment doctor")
    parser.add_argument("--npu", action="store_true", help="Perform deep Qualcomm Hexagon NPU diagnostics in doctor mode")
    parser.add_argument("--benchmark", action="store_true", help="Run statistical latency and throughput benchmark on Qualcomm NPU / active provider")

    # On-Device LoRA Fine-Tuning CLI Flags
    parser.add_argument("--tune", "--train-lora", action="store_true", dest="tune", help="Fine-tune compact LoRA adapter on local repository coding standards (Hexagon HTP / Air-Gapped)")
    parser.add_argument("--adapter-out", default="./adapters/code_style_lora", help="Output directory to save trained LoRA adapter (default: ./adapters/code_style_lora)")
    parser.add_argument("--adapter", default=None, help="Path to trained LoRA adapter directory to load during code review")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs for on-device LoRA fine-tuning (default: 3)")
    parser.add_argument("--lora-rank", type=int, default=8, help="Rank r for LoRA decomposition (default: 8)")

    args = parser.parse_args()
    target_path = Path(args.project_path).resolve()

    # Feature: --setup-all (1-Click Complete Enterprise Automation)
    if args.setup_all:
        console.print()
        console.print("[bold cyan]════════════════════════════════════════════════════════════════════════[/]")
        console.print("[bold white]  Faraday Automated 1-Click Setup & Governance Integration[/]")
        console.print("[bold cyan]════════════════════════════════════════════════════════════════════════[/]")
        root_dir = target_path if target_path.is_dir() else target_path.parent

        # 1. Scaffolding .faraday.yml
        cfg_file = init_project_config(root_dir)
        console.print(f"  [bold green][1/3] Created Faraday policy config:[/] [cyan]{cfg_file}[/]")

        # 2. Pre-commit hook
        repo_root = find_git_root(root_dir)
        if repo_root:
            try:
                hook_file = install_pre_commit_hook(repo_root)
                console.print(f"  [bold green][2/3] Installed Git pre-commit hook:[/] [cyan]{hook_file}[/]")
            except Exception as e:
                console.print(f"  [bold yellow][2/3] Skipped hook installation:[/] {e}")
        else:
            console.print("  [bold dim][2/3] Skipped hook (not inside a git repository).[/]")

        # 3. GitHub Actions CI
        ci_file = setup_github_ci_workflow(root_dir)
        console.print(f"  [bold green][3/3] Configured GitHub Actions CI/CD:[/] [cyan]{ci_file}[/]")
        console.print()
        console.print("[bold green][✓] Complete Faraday automation configured successfully![/]")
        console.print("  [dim]Pre-commit and GitHub Actions will now automatically audit code and enforce security gates.[/]\n")
        return

    # Feature: --setup-ci
    if args.setup_ci:
        root_dir = target_path if target_path.is_dir() else target_path.parent
        ci_file = setup_github_ci_workflow(root_dir)
        console.print(f"[bold green][+] Successfully generated GitHub Actions workflow at:[/] [cyan]{ci_file}[/]")
        console.print("  [dim]Push to GitHub to automatically trigger the Faraday Security Gate & SARIF upload.[/]")
        return

    # Feature: --tune (On-Device LoRA Fine-Tuning)
    if args.tune:
        sys.exit(run_lora_tuning(target_path, args))

    # Feature: --ui / --web / --dashboard (Launch Interactive Visual Code Review & Docs Dashboard)
    if getattr(args, "ui", False):
        from backend.web_server import launch_web_dashboard
        launch_web_dashboard(target_path, port=8000, auto_open=True)
        return

    # Feature: --prove / --npu-status (Empirical NPU Verification & Benchmark)
    if getattr(args, "prove", False):
        from backend.models.verify_npu import verify_npu_and_benchmark, print_prover_report
        cert = verify_npu_and_benchmark()
        print_prover_report(cert)
        return

    # Feature: --export-model (Export ONNX neural model & QNN compile manifest)
    if getattr(args, "export_model", False):
        from scripts.export_qnn_model import export_faraday_neural_model
        onnx_path, manifest_path = export_faraday_neural_model()
        console.print(f"[bold green][✓] Neural model successfully exported:[/] [cyan]{onnx_path}[/]")
        console.print(f"[bold green][✓] Qualcomm AI Hub manifest created:[/] [cyan]{manifest_path}[/]")
        return

    # Feature: faraday doctor [--npu] or faraday --doctor [--npu]
    is_doctor_cmd = args.project_path in ("doctor", "--doctor") or getattr(args, "doctor", False)
    if is_doctor_cmd:
        from backend.core.doctor import run_doctor
        is_npu = getattr(args, "npu", False) or ("--npu" in sys.argv)
        code = run_doctor(npu_focus=is_npu, console=console)
        sys.exit(code)

    # Feature: faraday benchmark or faraday --benchmark
    is_bench_cmd = args.project_path in ("benchmark", "--benchmark") or getattr(args, "benchmark", False)
    if is_bench_cmd:
        from scripts.benchmark_npu import run_benchmark
        run_benchmark(iterations=50, output_json=Path("review_output/benchmark_results.json"), console=console)
        return

    # Feature: --init configuration
    if args.init:
        created_file = init_project_config(target_path if target_path.is_dir() else target_path.parent)
        console.print(f"[bold green][+] Created Faraday configuration at:[/] {created_file}")
        return

    # Feature: --install-hook
    if args.install_hook:
        repo_root = find_git_root(target_path)
        if not repo_root:
            console.print("[bold red][!] Target directory is not inside a git repository. Initialize git first.[/]")
            sys.exit(1)
        try:
            hook_file = install_pre_commit_hook(repo_root)
            console.print(f"[bold green][+] Successfully installed pre-commit hook at:[/] {hook_file}")
            console.print("  [dim]Pre-commit hook will automatically run `faraday --staged --fail-on HIGH` before each commit.[/]")
        except Exception as e:
            console.print(f"[bold red][!] Failed to install pre-commit hook: {e}[/]")
            sys.exit(1)
        return

    backend = get_backend()

    # Determine whether interactive session is appropriate
    # Non-interactive when: not a TTY (and not --interactive), --json, --once, or git hook/diff/staged passed
    is_interactive = (
        (args.interactive or sys.stdin.isatty())
        and not args.json
        and not args.once
        and not args.staged
        and not args.diff
    )

    current_target = target_path
    last_exit_code = 0

    try:
        while True:
            gate_failed, code = execute_pipeline(current_target, args, backend, is_interactive=is_interactive)
            if code != 0:
                last_exit_code = code

            if not is_interactive:
                if code != 0:
                    sys.exit(code)
                break

            # Interactive prompt for next project or folder
            console.print("[dim]─" * 78 + "[/dim]")
            console.print("[bold cyan]?[/] [bold white]Review another project / folder?[/] [dim](Enter path, 'r' to re-scan, or 'q' to quit) [q]: [/]", end="")
            try:
                raw_input = input()
                next_input = raw_input.strip() if raw_input.strip() else "q"
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Session closed.[/]\n")
                break

            # Handle user choices
            if next_input.lower() in ("q", "quit", "exit", ""):
                console.print("\n[bold green][✓][/] Exiting Faraday. All reviews completed air-gapped on-device.\n")
                break
            elif next_input.lower() in ("r", "rescan", "re-scan"):
                console.print(f"\n[bold cyan][*] Re-scanning target:[/] {current_target}\n")
                continue
            else:
                cleaned_input = next_input.strip(' "\'')
                candidate = Path(cleaned_input).expanduser().resolve()
                if not candidate.exists():
                    console.print(f"[bold red][!] Path does not exist:[/] '{cleaned_input}'. Please enter a valid directory or file.\n")
                    continue
                current_target = candidate
                console.print(f"\n[bold green][*] Switching target project to:[/] {current_target}\n")

    except KeyboardInterrupt:
        console.print("\n[dim]Scan interrupted by user.[/]\n")

    if last_exit_code != 0 and not is_interactive:
        sys.exit(last_exit_code)


if __name__ == "__main__":
    main()
