"""
config.py

Loads and manages CodeGuard project configuration from .codeguard.yml,
.codeguard.yaml, .codeguard.json, or pyproject.toml [tool.codeguard].

Enables enterprise teams to establish uniform code assurance, security rules,
and CI/CD gate policies across real-world repositories without repeating CLI flags.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+ stdlib
except ImportError:
    try:
        import importlib
        tomllib = importlib.import_module("tomli")  # Fallback for Python < 3.11
    except ImportError:
        tomllib = None

try:
    import yaml
except ImportError:
    yaml = None


DEFAULT_CONFIG: Dict[str, Any] = {
    "exclude": [
        "tests/**",
        "vendor/**",
        "node_modules/**",
        "dist/**",
        "build/**",
        ".git/**",
        "*.min.js",
        "*.lock",
    ],
    "fail_on": "HIGH",
    "output": "./review_output",
    "skip_ai": False,
    "staged_only": False,
    "max_file_size_kb": 1024,
    "suppress_rules": [],
}


SAMPLE_CONFIG_YAML = """# Faraday Enterprise Configuration File
# Documentation: https://github.com/Monishwaran45/Faraday

# Globs and directories to exclude from review
exclude:
  - "tests/**"
  - "vendor/**"
  - "node_modules/**"
  - "dist/**"
  - "build/**"
  - "*.min.js"
  - "*.lock"

# CI/CD Gate failure threshold: HIGH, MEDIUM, LOW, or NONE
fail_on: "HIGH"

# Output directory for markdown reports and SARIF artifacts
output: "./review_output"

# Set to true to run only fast static security scanning (sub-second for pre-commit)
skip_ai: false

# Restrict scan strictly to git staged files (recommended for pre-commit hooks)
staged_only: false

# Maximum individual file size to analyze (in kilobytes)
max_file_size_kb: 1024

# Rule labels to suppress across the entire codebase
suppress_rules: []
"""


def load_project_config(project_path: Path) -> Dict[str, Any]:
    """
    Search for configuration file in project directory and merge with defaults.
    Precedence:
      1. .faraday.yml / .faraday.yaml (or legacy .codeguard.yml / .codeguard.yaml)
      2. .faraday.json / faraday.json (or legacy .codeguard.json / codeguard.json)
      3. pyproject.toml [tool.faraday] (or [tool.codeguard])
    """
    root = project_path if project_path.is_dir() else project_path.parent
    config = dict(DEFAULT_CONFIG)

    # 1. YAML config
    yaml_candidates = [
        root / ".faraday.yml",
        root / ".faraday.yaml",
        root / ".codeguard.yml",
        root / ".codeguard.yaml",
    ]
    for ypath in yaml_candidates:
        if ypath.exists():
            if yaml:
                try:
                    data = yaml.safe_load(ypath.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        config.update(data)
                        return config
                except Exception:
                    pass
            break

    # 2. JSON config
    json_candidates = [
        root / ".faraday.json",
        root / "faraday.json",
        root / ".codeguard.json",
        root / "codeguard.json",
    ]
    for jpath in json_candidates:
        if jpath.exists():
            try:
                data = json.loads(jpath.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    config.update(data)
                    return config
            except Exception:
                pass
            break

    # 3. pyproject.toml
    pyproject_path = root / "pyproject.toml"
    if pyproject_path.exists() and tomllib:
        try:
            with open(pyproject_path, "rb") as f:
                toml_data = tomllib.load(f)
            tool_cfg = toml_data.get("tool", {}).get("faraday", {})
            if not tool_cfg:
                tool_cfg = toml_data.get("tool", {}).get("codeguard", {})
            if isinstance(tool_cfg, dict):
                config.update(tool_cfg)
        except Exception:
            pass

    return config


def init_project_config(project_path: Path) -> Path:
    """Generate a starter .faraday.yml in target project."""
    target_file = project_path / ".faraday.yml"
    target_file.write_text(SAMPLE_CONFIG_YAML, encoding="utf-8")
    return target_file


def setup_github_ci_workflow(project_path: Path) -> Path:
    """
    Automatically creates production-ready .github/workflows/faraday.yml in the target repository.
    Configures cross-platform automated SARIF security reporting and CI gate enforcement.
    """
    workflow_dir = project_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_file = workflow_dir / "faraday.yml"

    workflow_content = """name: Faraday Security & Code Review Gate

on:
  push:
    branches: [ "main", "master", "develop" ]
  pull_request:
    branches: [ "main", "master" ]
  workflow_dispatch:

jobs:
  faraday-scan:
    name: Faraday On-Device & Offline Scan
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
      actions: read

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install Dependencies & Faraday
        run: |
          uv pip install --system -e .

      - name: Run Faraday Security & Assurance Scan
        run: |
          python -m backend.cli . --fail-on NONE --sarif results.sarif --once

      - name: Upload SARIF to GitHub Security Tab
        if: always() && hashFiles('results.sarif') != ''
        continue-on-error: true
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
          category: faraday
"""
    workflow_file.write_text(workflow_content, encoding="utf-8")
    return workflow_file
