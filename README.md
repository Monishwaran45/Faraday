# Faraday — Air-Gapped AI Code Assurance & Security Copilot

**Built for the Snapdragon® AI Lab Build & Present Challenge 2026**

*Named after the Faraday cage—symbolizing 100% physical and data isolation—Faraday provides enterprise teams with complete code privacy, offline neural intelligence, and zero data egress.*

Faraday is an offline, on-device AI code assurance engine that reviews source code for bugs, hardcoded credentials, and security vulnerabilities, and synthesizes docstrings and architectural documentation — running entirely on-device on the Qualcomm Snapdragon® X Elite Hexagon NPU.

Engineered for enterprise developers in defense, banking, healthcare, and high-compliance environments who cannot transmit proprietary IP or source code to cloud AI APIs.

---

## 🛡️ Why "Faraday"?

A **Faraday cage** blocks external electromagnetic fields, creating an impenetrable barrier. Similarly, **Faraday** creates an impenetrable security boundary around your codebase:
- **100% Air-Gapped & Offline:** Operates with WiFi physically disabled. Zero outbound telemetry, zero cloud dependencies.
- **Hardware-Accelerated Intelligence:** Direct execution on Snapdragon® Hexagon NPU via Qualcomm Neural Network (QNN) SDK.
- **Zero Data Egress:** Your source code, proprietary algorithms, and enterprise secrets never leave your silicon.

---

## Key Enterprise Features

- **Snapdragon® Hexagon NPU Acceleration:** Utilizes compiled QNN context binaries (`Qwen2-7B-Instruct` `w4a16`) running directly on the Qualcomm Snapdragon X Elite NPU.
- **Interactive Multi-Project Terminal UI:** Autonomous Rich interactive terminal interface that reviews a project, presents reports, and interactively prompts for the next project location.
- **Git Staged & Diff Scanning:** Review only staged files (`faraday --staged`) or pull request branch diffs (`faraday --diff main`) in milliseconds on large repositories.
- **OASIS SARIF v2.1.0 Export:** Generates industry-standard SARIF reports (`--sarif`) with MITRE CWE taxonomy mapping for native integration into GitHub Code Scanning, GitLab SAST, and VS Code.
- **Pre-Commit Hook Integration:** Automated one-click hook installation (`faraday --install-hook`) and native support for the standard `pre-commit` framework via `.pre-commit-hooks.yaml`.
- **Project Configuration Files:** Centralized repository policies via `.faraday.yml`, `.faraday.json`, or `pyproject.toml` (`[tool.faraday]`). Initialize in any repo with `faraday --init`.
- **Mathematical Shannon Entropy Secret Detection:** Flags high-entropy strings and modern API tokens (AWS, GCP, GitHub, OpenAI, Anthropic, HuggingFace, Slack, PyPI, NPM, Private Keys).
- **CI/CD Quality Gates:** Break pull request builds on critical flaws with configurable thresholds (`--fail-on HIGH`, `--fail-on MEDIUM`).

---

## How It Works

```
project files / git staged files
     │
     ▼
file_scanner.py      ──► AST chunking for Python & JS/TS function parsing
     │
     ▼
secret_scanner.py    ──► Shannon entropy + regex: Cloud tokens, AI keys, DB URIs, SSL bypass
     │
     ▼
llm_reviewer.py      ──► On-device Snapdragon Hexagon NPU neural review & docstrings
     │
     ▼
report_builder.py    ──► Synthesizes REVIEW_REPORT.md, GENERATED_DOCSTRINGS.md,
                         GENERATED_README.md, and OASIS SARIF v2.1.0
```

---

## ⚡ How to Execute the Project

### 1. Prerequisites & Environment Setup

Make sure you have Python 3.11+ installed. We recommend using `uv` for fast package management:

```bash
# Clone or navigate to the repository
cd "Qualcomm Snapdragon"

# Create virtual environment and install dependencies
uv sync
# Or using standard pip:
# pip install -e .
```

### 2. Basic Execution (Scan Current Repository or Folder)

You can run Faraday using the package CLI command, `uv run`, or directly via Python:

```bash
# Run on the current repository:
uv run faraday .

# Run on the seeded sample project:
uv run faraday demo/sample_project

# Or directly via Python:
uv run python main.py demo/sample_project
```

*(Note: `codeguard` remains registered as a backwards-compatible alias).*

### 3. Interactive Multi-Project Review Mode

Faraday features an interactive continuous review workflow. When you finish scanning one project, the Rich terminal prompts you for the next location:

```bash
uv run faraday demo/sample_project
```
After the report is presented:
```text
──────────────────────────────────────────────────────────────────────────────
? Review another project / folder? (Enter path, 'r' to re-scan, or 'q' to quit) [q]: 
```
- **Type another project path** (e.g. `C:\Users\Asus-2025\Downloads\ETA` or `tests`): Faraday immediately switches target and reviews the new codebase.
- **Type `r`**: Re-scans the current project (instantly verifies your bug fixes).
- **Type `q` (or press Enter)**: Exits Faraday cleanly.

### 4. Scanning Any External Real-World Project

You can point Faraday at any folder or external repository:

```bash
uv run faraday "C:\Users\Asus-2025\Downloads\ETA"
```

### 5. Running in Non-Interactive / CI Mode (`--once`)

If you want Faraday to run a single scan and exit immediately without prompting:

```bash
uv run faraday . --once
```

### 6. Sub-Second Git Staged Scanning (Pre-Commit Mode)

To scan only the files you have staged in git:

```bash
uv run faraday --staged --fail-on HIGH
```

### 7. Exporting Industry-Standard SARIF for GitHub Security

Export OASIS SARIF v2.1.0 to upload to GitHub Code Scanning or view in VS Code:

```bash
uv run faraday demo/sample_project --sarif review_output/results.sarif
```

### 8. Machine-Readable JSON Output (CI/CD Pipelines)

```bash
uv run faraday demo/sample_project --json
```

### 9. Benchmarking Model Backend & Inference Latency

To inspect the active NPU execution provider and measure single-inference latency:

```bash
uv run python backend/models/model_backend.py
```

---

## 📂 Where to Find Output Reports

All artifacts are generated in the `--output` directory (default: `./review_output`):

1. **`review_output/REVIEW_REPORT.md`**: Comprehensive report containing deterministic static security findings (credentials, dangerous builtins) and neural AI code review notes.
2. **`review_output/GENERATED_DOCSTRINGS.md`**: Synthesized docstrings for all parsed functions and classes across the project.
3. **`review_output/GENERATED_README.md`**: Complete, production-grade project README dynamically synthesized from the codebase's modules, endpoints, and architecture.
4. **`review_output/*.sarif`**: OASIS SARIF v2.1.0 file with MITRE CWE mappings for GitHub Security tab integration.

---

## Real-World Project Integration

### Initialize Configuration in Your Repo
Generate a customized `.faraday.yml` configuration:
```bash
uv run faraday --init
```

### Automatic Git Pre-Commit Hook Installation
Install Faraday to run automatically before every git commit:
```bash
uv run faraday --install-hook
```

Or add to your existing `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/faraday-ai/faraday
    rev: v1.0.0
    hooks:
      - id: faraday
        args: ["--staged", "--fail-on", "HIGH"]
```

### Pull Request Branch Diff Scan
In CI or local feature branches, review only files modified against `main`:
```bash
uv run faraday --diff main --fail-on HIGH --sarif results.sarif
```

### GitHub Actions CI/CD Workflow
Drop `.github/workflows/faraday.yml` into your repository:
```yaml
name: Faraday Security Gate
on: [push, pull_request]

jobs:
  faraday-scan:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install uv && uv pip install --system -e .
      - run: faraday . --fail-on HIGH --sarif results.sarif
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: results.sarif
```

---

## Production Project Layout

```
Qualcomm Snapdragon/
├── backend/
│   ├── core/
│   │   ├── config.py           # .faraday.yml, JSON, & pyproject.toml loader
│   │   ├── git_utils.py        # Git staged/diff file detection & hook installer
│   │   ├── sarif_builder.py    # OASIS SARIF v2.1.0 generator for CI/CD & CWE mapping
│   │   ├── file_scanner.py     # AST-based Python parser & JS/TS function chunker
│   │   ├── secret_scanner.py   # Shannon entropy & static vulnerability scanner
│   │   ├── llm_reviewer.py     # Neural review & documentation generation
│   │   └── report_builder.py   # Synthesis of security & review markdown reports
│   ├── models/
│   │   └── model_backend.py    # Snapdragon Hexagon NPU QNN backend & mock fallback
│   └── cli.py                  # Autonomous Rich interactive terminal UI
├── demo/
│   ├── sample_project/         # Multi-file test codebase
│   │   ├── database.py
│   │   ├── inventory.py
│   │   └── utils.py
│   └── review_output/          # Generated markdown reports
├── models/
│   └── qwen2-7b-qnn/           # Compiled Snapdragon X Elite QNN context binaries
├── tests/
│   ├── test_config.py          # Configuration loading & init tests
│   ├── test_git_utils.py       # Git integration tests
│   ├── test_sarif_builder.py   # SARIF v2.1.0 output & CWE mapping tests
│   ├── test_file_scanner.py    # Python & JS/TS function chunking tests
│   ├── test_secret_scanner.py  # Static vulnerability & Shannon entropy tests
│   ├── test_model_backend.py   # Backend contract & heuristic precision tests
│   └── test_report_builder.py  # Markdown synthesis & compliance tests
├── .github/workflows/
│   └── codeguard.yml           # CI/CD GitHub Actions workflow template
├── .pre-commit-hooks.yaml      # Standard pre-commit framework manifest
├── pyproject.toml              # Build config, dependencies, faraday & codeguard CLI scripts
├── requirements.txt            # Pinned requirements
├── .gitignore                  # Production ignore rules
└── main.py                     # Convenience top-level entrypoint
```

---

## Running Automated Tests

Run the full 23-test suite covering all core and enterprise modules:

```bash
uv run pytest
```

---

## Demo Script (Air-Gapped Showcase)

1. **Visibly disable WiFi** on the Snapdragon laptop.
2. Run Faraday against the demo project:
   ```bash
   uv run faraday demo/sample_project --sarif demo_sarif.sarif
   ```
3. Show the **Static Security Findings** catching credentials, high-entropy secrets, and SQL concatenation immediately.
4. Show the **On-Device Neural Review** analyzing logic on the **Snapdragon Hexagon NPU**.
5. Inspect the generated **OASIS SARIF report** (`demo_sarif.sarif`), docstrings, and synthesized README in `review_output/`.
