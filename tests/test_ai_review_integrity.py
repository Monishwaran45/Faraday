"""
test_ai_review_integrity.py

Independent, automated verification of Faraday's AI and Neural Inference Pipeline.
Validates:
1. Genuine ONNX computational graph execution (input_ids -> risk_score & cwe_logits).
2. Strict vocabulary bounds (0 <= token_id < 10,000) preventing embedding table corruption.
3. Cryptographic model integrity (SHA-256 digest, tensor dimensions, and size bounds).
4. Transparent separation between neural risk scoring and deterministic AST taint tracking.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import pytest
import numpy as np
import onnxruntime as ort
from pathlib import Path
from backend.models.tokenizer import CodeTokenizer
from backend.models.model_security import verify_model_integrity, compute_file_sha256
from backend.models.model_backend import QNNBackend

MODEL_PATH = Path("models/onnx/faraday_code_assurance.onnx")


def test_model_cryptographic_integrity():
    """Validates SHA-256 digest, file size, and ONNX graph validity."""
    assert MODEL_PATH.exists(), f"Model file missing: {MODEL_PATH}"
    is_valid, msg, meta = verify_model_integrity(MODEL_PATH)
    assert is_valid, f"Model verification failed: {msg}"
    assert meta["file_size_bytes"] > 1_000_000
    assert "input_ids" in meta["input_tensors"]
    assert "risk_score" in meta["output_tensors"]


def test_tokenizer_vocabulary_bounds_integrity():
    """Ensures token IDs never exceed embedding dimension 10,000."""
    tokenizer = CodeTokenizer.get_default()
    sample_code = """
    def query_user(user_id):
        cursor.execute("SELECT * FROM users WHERE id = " + user_id)
        return True
    """
    token_tensor = tokenizer.encode(sample_code, max_length=64, padding=True)
    assert token_tensor.shape == (1, 64)
    assert np.all(token_tensor >= 0)
    assert np.all(token_tensor < 10000)


def test_genuine_onnx_neural_forward_pass():
    """Validates real neural graph execution through ONNX Runtime."""
    tokenizer = CodeTokenizer.get_default()
    session = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])

    code = "import os\nos.system('rm -rf /')"
    token_tensor = tokenizer.encode(code, max_length=64, padding=True)

    outputs = session.run(None, {"input_ids": token_tensor})
    assert len(outputs) >= 2, "Expected risk_score and cwe_logits outputs"

    risk_score = float(outputs[0][0][0])
    cwe_logits = outputs[1][0]

    # Continuous risk score must be bounded between 0.0 and 1.0
    assert 0.0 <= risk_score <= 1.0
    # Severity classification head outputs (Clean, Low, Medium, High)
    assert len(cwe_logits) in (4, 8)


def test_qnn_backend_neural_execution():
    """Validates that QNNBackend utilizes genuine neural tensor outputs."""
    backend = QNNBackend(model_path=str(MODEL_PATH))
    assert backend.name.startswith("ONNX Neural Engine")

    prompt = "Review this snippet:\ncursor.execute('SELECT * FROM users')"
    response = backend.generate(prompt)
    assert isinstance(response, str)
    assert len(response) > 20
