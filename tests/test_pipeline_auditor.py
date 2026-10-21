"""
tests/test_pipeline_auditor.py

Exhaustive tests for CI/CD Build Pipeline & AI Agent Permission Auditor.
"""

from pathlib import Path
from backend.core.pipeline_auditor import audit_codebase_pipelines


def test_detects_curl_pipe_bash_in_workflow(tmp_path: Path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    wf_file = wf_dir / "deploy.yml"
    wf_file.write_text(
        """
name: Deploy
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: curl -sSL https://example.com/install.sh | bash
""",
        encoding="utf-8",
    )

    report = audit_codebase_pipelines(tmp_path)
    assert any(f.rule_id == "PIPE-SEC-001" and f.severity == "HIGH" for f in report.findings)


def test_detects_unpinned_action_and_write_all(tmp_path: Path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    wf_file = wf_dir / "ci.yml"
    wf_file.write_text(
        """
name: CI
on: [push]
permissions: write-all
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@master
""",
        encoding="utf-8",
    )

    report = audit_codebase_pipelines(tmp_path)
    assert any(f.rule_id == "PIPE-SEC-003" for f in report.findings)
    assert any(f.rule_id == "PIPE-SEC-004" for f in report.findings)


def test_detects_dockerfile_hardcoded_secret(tmp_path: Path):
    df = tmp_path / "Dockerfile"
    df.write_text(
        """
FROM python:3.11-slim
ENV API_SECRET_KEY=supersecret12345
RUN useradd -u 1000 app
USER app
CMD ["python", "app.py"]
""",
        encoding="utf-8",
    )

    report = audit_codebase_pipelines(tmp_path)
    assert any(f.rule_id == "DOCKER-SEC-001" and f.severity == "HIGH" for f in report.findings)


def test_detects_ai_agent_unrestricted_shell(tmp_path: Path):
    agent_cfg = tmp_path / "agent_config.json"
    agent_cfg.write_text(
        """
{
  "name": "DevCopilot",
  "execute_commands": true,
  "workspace_paths": ["/"]
}
""",
        encoding="utf-8",
    )

    report = audit_codebase_pipelines(tmp_path)
    assert any(f.rule_id == "AGENT-SEC-001" and f.severity == "HIGH" for f in report.findings)
    assert any(f.rule_id == "AGENT-SEC-002" and f.severity == "HIGH" for f in report.findings)


def test_clean_pipeline_has_zero_findings(tmp_path: Path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    wf_file = wf_dir / "secure_ci.yml"
    wf_file.write_text(
        """
name: Secure CI
on: [push]
permissions:
  contents: read
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
        with:
          persist-credentials: false
""",
        encoding="utf-8",
    )

    report = audit_codebase_pipelines(tmp_path)
    assert len(report.findings) == 0
    assert report.has_findings is False
