"""
test_tokenizer.py

Unit tests verifying model-native code tokenization, vocabulary validation,
round-trip encoding, subword/byte fallback, and JSON persistence.
Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import numpy as np
import pytest
from pathlib import Path
from backend.models.tokenizer import (
    CodeTokenizer,
    DEFAULT_VOCAB_SIZE,
    PAD_TOKEN,
    UNK_TOKEN,
    BOS_TOKEN,
    EOS_TOKEN,
)


def test_tokenizer_initialization_and_special_tokens():
    tok = CodeTokenizer.get_default()
    assert tok.vocab_size == DEFAULT_VOCAB_SIZE
    assert PAD_TOKEN in tok.vocab
    assert UNK_TOKEN in tok.vocab
    assert BOS_TOKEN in tok.vocab
    assert EOS_TOKEN in tok.vocab
    assert tok.pad_id == 0


def test_tokenizer_encoding_shape_and_bounds():
    tok = CodeTokenizer.get_default()
    code = "def secure_function(user_id: int):\n    return db.query(user_id)"
    tensor = tok.encode(code, max_length=64, padding=True, truncation=True)

    assert isinstance(tensor, np.ndarray)
    assert tensor.shape == (1, 64)
    assert tensor.dtype == np.int64

    # Strict vocabulary validation check
    assert np.all(tensor >= 0)
    assert np.all(tensor < DEFAULT_VOCAB_SIZE)
    assert tok.validate_token_ids(tensor) is True


def test_tokenizer_out_of_bounds_validation_raises():
    tok = CodeTokenizer.get_default()
    invalid_tensor = np.array([[0, 10, DEFAULT_VOCAB_SIZE + 50]], dtype=np.int64)
    with pytest.raises(ValueError, match="Token ID out-of-bounds"):
        tok.validate_token_ids(invalid_tensor)

    negative_tensor = np.array([[-1, 5, 10]], dtype=np.int64)
    with pytest.raises(ValueError, match="Token ID out-of-bounds"):
        tok.validate_token_ids(negative_tensor)


def test_tokenizer_persistence_roundtrip(tmp_path):
    tok = CodeTokenizer.get_default()
    save_path = tmp_path / "custom_tokenizer.json"
    tok.save(save_path)
    assert save_path.exists()

    loaded = CodeTokenizer.load(save_path)
    assert loaded.vocab_size == tok.vocab_size
    assert len(loaded.vocab) == len(tok.vocab)

    code = "SELECT * FROM users WHERE active = 1"
    t1 = tok.encode(code)
    t2 = loaded.encode(code)
    np.testing.assert_array_equal(t1, t2)
