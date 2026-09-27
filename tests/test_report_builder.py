import pytest
from pathlib import Path
from backend.core.secret_scanner import SecretFinding
from backend.core.llm_reviewer import ChunkReview
from backend.core.report_builder import build_report

def test_build_report_generates_files(tmp_path):
    output_dir = tmp_path / "out"
    findings = [
        SecretFinding(
            file_path="auth.py",
            line_number=5,
            label="Hardcoded Password",
            severity="High",
            snippet="PASSWORD = 'secret'",
        )
    ]
    reviews = [
        ChunkReview(
            file_path="auth.py",
            chunk_name="login",
            start_line=1,
            end_line=10,
            review_raw="ISSUES:\n1. Insecure auth\nSEVERITY:\nHigh\nSUGGESTED_FIX:\nUse bcrypt",
            docstring='"""Handles user authentication."""',
        )
    ]
    readme = "# Test Readme\n\nProject overview."

    paths = build_report(findings, reviews, readme, str(output_dir))

    assert Path(paths["report"]).exists()
    assert Path(paths["docstrings"]).exists()
    assert Path(paths["readme"]).exists()

    report_content = Path(paths["report"]).read_text(encoding="utf-8")
    assert "Hardcoded Password" in report_content
    assert "Insecure auth" in report_content
