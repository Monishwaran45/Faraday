"""
test_scan_card.py

Unit tests for Faraday Shareable Scan Card:
1. ScanCard instantiation and metrics mapping.
2. Markdown card output.
3. Standalone SVG generation.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from pathlib import Path
from backend.core.scan_card import generate_scan_card


def test_scan_card_generation_and_formats(tmp_path: Path):
    """Verifies that ScanCard generates valid Markdown and SVG outputs."""
    svg_file = tmp_path / "card.svg"
    card = generate_scan_card(
        findings_detected=12,
        findings_resolved=12,
        findings_remaining=0,
        tests_verified=5,
        execution_mode="Qualcomm Hexagon NPU (HTP v73)",
        passport_digest="1234567890abcdef1234567890abcdef",
        repo_revision="a1b2c3d4e5f6",
        export_svg_path=svg_file,
    )

    assert card.findings_resolved == 12
    assert card.tests_verified == 5

    md = card.to_markdown()
    assert "FARADAY SCAN REPORT" in md
    assert "Findings Resolved: 12" in md
    assert "Tests Verified:    5" in md
    assert "100% Zero-Egress Verified" in md

    assert svg_file.exists()
    svg_text = svg_file.read_text(encoding="utf-8")
    assert "<svg" in svg_text
    assert "FARADAY VERIFIED SCAN REPORT" in svg_text
    assert "12" in svg_text
    assert "5" in svg_text
