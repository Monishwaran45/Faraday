from pathlib import Path
from backend.core.secret_scanner import SecretFinding
from backend.core.llm_reviewer import ChunkReview
from backend.core.sarif_builder import generate_sarif_report, write_sarif_file


def test_generate_sarif_report(tmp_path):
    secret_findings = [
        SecretFinding(
            file_path=str(tmp_path / "app.py"),
            line_number=10,
            label="Hardcoded AWS Access Key",
            severity="High",
            snippet="AKIAIOSFODNN7EXAMPLE",
        )
    ]
    chunk_reviews = [
        ChunkReview(
            file_path=str(tmp_path / "app.py"),
            chunk_name="calculate_tax",
            start_line=1,
            end_line=20,
            review_raw="ISSUES:\n1. Missing bounds check\nSEVERITY:\nMedium\nSUGGESTED_FIX:\nAdd validation",
            docstring='"""Tax calculation."""',
        )
    ]

    sarif = generate_sarif_report(secret_findings, chunk_reviews, tmp_path)

    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "Faraday"
    assert len(run["results"]) == 2

    # Check high severity mapped to error
    high_result = [r for r in run["results"] if r["level"] == "error"][0]
    assert "Hardcoded AWS Access Key" in high_result["message"]["text"]

    # Test writing to file
    out_file = tmp_path / "output.sarif"
    written = write_sarif_file(sarif, out_file)
    assert written.exists()
    assert '"version": "2.1.0"' in written.read_text(encoding="utf-8")
