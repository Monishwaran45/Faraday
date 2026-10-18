"""
test_silicon_passport.py

Unit tests for Faraday Silicon Passport:
1. Silicon Passport generation and hardware/model provenance capture.
2. Latency percentiles calculation.
3. Air-gapped network egress validation (0 bytes).
4. Tamper-evident signature calculation and tamper detection.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from pathlib import Path
from backend.core.silicon_passport import (
    generate_silicon_passport,
    verify_passport_integrity,
)


def test_generate_silicon_passport_telemetry(tmp_path: Path):
    """Verifies that generate_silicon_passport records hardware truth and valid signature."""
    export_file = tmp_path / "silicon_passport.json"
    passport = generate_silicon_passport(iterations=5, export_path=export_file)

    assert passport.passport_id.startswith("FSP-")
    assert passport.model_provenance["model_name"] == "FaradayCodeAssuranceNeuralNet"
    assert passport.model_provenance["parameters"] == 1413901
    assert len(passport.model_provenance["sha256"]) == 64

    # Telemetry checks
    tm = passport.measured_telemetry
    assert tm["p50_latency_ms"] >= 0.0
    assert tm["p95_latency_ms"] >= tm["p50_latency_ms"]
    assert tm["network_egress_bytes"] == 0
    assert tm["air_gapped_verified"] is True

    # Digital signature check
    assert len(passport.tamper_evident_signature) == 64
    assert export_file.exists()


def test_passport_tamper_detection():
    """Verifies that altering any field in the passport fails integrity verification."""
    passport = generate_silicon_passport(iterations=5)
    passport_dict = passport.to_dict()

    # Authentic passport passes integrity
    assert verify_passport_integrity(passport_dict) is True

    # Tampered passport fails integrity
    tampered_dict = dict(passport_dict)
    tampered_dict["measured_telemetry"]["mean_latency_ms"] = 0.001
    assert verify_passport_integrity(tampered_dict) is False
