"""
tokenizer.py

Production-grade, model-native Code Tokenizer for Faraday.
Optimized for on-device inference on the Qualcomm Snapdragon Hexagon NPU.
Provides deterministic subword and byte-level tokenization matching the
FaradayCodeAssuranceNeuralNet vocabulary (10,000 tokens) with strict
vocabulary ID validation and JSON configuration persistence.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Union, Optional
import numpy as np

DEFAULT_VOCAB_SIZE = 10000
PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"
BOS_TOKEN = "<s>"
EOS_TOKEN = "</s>"

SPECIAL_TOKENS = [PAD_TOKEN, UNK_TOKEN, BOS_TOKEN, EOS_TOKEN]

# Standard programming language keywords and tokens (Python, JS, TS, SQL, Shell, C/C++)
COMMON_CODE_KEYWORDS = [
    "def", "class", "return", "import", "from", "as", "if", "elif", "else",
    "for", "while", "break", "continue", "try", "except", "finally", "raise",
    "with", "yield", "async", "await", "pass", "lambda", "in", "is", "not",
    "and", "or", "True", "False", "None", "self", "cls", "__init__",
    "function", "const", "let", "var", "typeof", "instanceof", "new", "delete",
    "this", "switch", "case", "default", "catch", "throw", "debugger", "export",
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "UPDATE", "SET", "DELETE",
    "JOIN", "INNER", "LEFT", "RIGHT", "ON", "GROUP", "BY", "ORDER", "HAVING",
    "LIMIT", "UNION", "ALL", "AND", "OR", "NOT", "NULL", "TRUE", "FALSE",
    "int", "float", "str", "bool", "list", "dict", "set", "tuple", "bytes",
    "void", "char", "double", "short", "long", "struct", "typedef", "sizeof",
    "public", "private", "protected", "static", "final", "abstract", "interface",
    "eval", "exec", "os", "sys", "subprocess", "requests", "pickle", "yaml",
    "token", "secret", "password", "key", "auth", "jwt", "bearer", "session",
    "api", "database", "query", "cursor", "execute", "connection", "http", "https",
    "url", "path", "file", "open", "read", "write", "close", "data", "payload",
    "response", "request", "header", "cookie", "params", "json", "xml", "html"
]

COMMON_OPERATORS = [
    "(", ")", "[", "]", "{", "}", ":", ",", ";", ".", "=", "==", "!=",
    "<=", ">=", "<", ">", "+", "-", "*", "/", "//", "%", "**", "&", "|",
    "^", "~", "<<", ">>", "+=", "-=", "*=", "/=", "->", "=>", "@", "$",
    "?", "!", "\"", "'", "`", "\\", "\n", "\t", "    "
]


class CodeTokenizer:
    """
    Model-native code tokenizer for Qualcomm Hexagon NPU code assurance models.
    Maps source code tokens to integer IDs strictly bounded within [0, vocab_size - 1].
    """

    def __init__(self, vocab: Optional[Dict[str, int]] = None, vocab_size: int = DEFAULT_VOCAB_SIZE):
        self.vocab_size = vocab_size
        if vocab is not None:
            self.vocab = dict(vocab)
        else:
            self.vocab = self._build_default_vocab()
        
        self.inv_vocab = {v: k for k, v in self.vocab.items()}
        self.pad_id = self.vocab.get(PAD_TOKEN, 0)
        self.unk_id = self.vocab.get(UNK_TOKEN, 1)
        self.bos_id = self.vocab.get(BOS_TOKEN, 2)
        self.eos_id = self.vocab.get(EOS_TOKEN, 3)

    def _build_default_vocab(self) -> Dict[str, int]:
        vocab: Dict[str, int] = {}
        # 1. Special tokens
        for token in SPECIAL_TOKENS:
            vocab[token] = len(vocab)
        
        # 2. Byte tokens (0-255) for complete unicode and ASCII fallback
        for b in range(256):
            b_char = f"<byte_{b}>"
            if b_char not in vocab:
                vocab[b_char] = len(vocab)
        
        # 3. Operators and syntax
        for op in COMMON_OPERATORS:
            if op not in vocab and len(vocab) < self.vocab_size - 500:
                vocab[op] = len(vocab)
                
        # 4. Code keywords
        for kw in COMMON_CODE_KEYWORDS:
            if kw not in vocab and len(vocab) < self.vocab_size - 200:
                vocab[kw] = len(vocab)
                
        return vocab

    def tokenize(self, text: str) -> List[str]:
        """Split code string into lexically coherent tokens."""
        if not text:
            return []
        # Pattern captures words/identifiers, symbols, punctuation, and whitespace blocks
        pattern = re.compile(r"""[a-zA-Z_]\w*|[0-9]+|==|!=|<=|>=|->|=>|\*\*|//|\n|[^\s\w]|\s+""")
        tokens = pattern.findall(text)
        return tokens

    def encode(
        self,
        text: str,
        max_length: int = 64,
        padding: bool = True,
        truncation: bool = True,
        add_special_tokens: bool = False
    ) -> np.ndarray:
        """
        Encode raw code text into model-compliant input_ids tensor.
        Validates that all token IDs are strictly within [0, vocab_size - 1].
        """
        raw_tokens = self.tokenize(text)
        token_ids: List[int] = []

        if add_special_tokens:
            token_ids.append(self.bos_id)

        for tok in raw_tokens:
            if tok in self.vocab:
                token_ids.append(self.vocab[tok])
            else:
                # Subword/byte fallback
                for byte_val in tok.encode("utf-8", errors="replace"):
                    byte_tok = f"<byte_{byte_val}>"
                    token_ids.append(self.vocab.get(byte_tok, self.unk_id))

        if add_special_tokens:
            token_ids.append(self.eos_id)

        if truncation and len(token_ids) > max_length:
            token_ids = token_ids[:max_length]

        if padding and len(token_ids) < max_length:
            token_ids.extend([self.pad_id] * (max_length - len(token_ids)))

        tensor = np.array([token_ids[:max_length]], dtype=np.int64)
        self.validate_token_ids(tensor)
        return tensor

    def decode(self, token_ids: Union[List[int], np.ndarray], skip_special_tokens: bool = True) -> str:
        """Decode integer token IDs back to a readable string."""
        if isinstance(token_ids, np.ndarray):
            token_ids = token_ids.flatten().tolist()

        out_parts: List[str] = []
        for tid in token_ids:
            tok = self.inv_vocab.get(tid, UNK_TOKEN)
            if skip_special_tokens and tok in SPECIAL_TOKENS:
                continue
            if tok.startswith("<byte_") and tok.endswith(">"):
                try:
                    b_val = int(tok[6:-1])
                    out_parts.append(chr(b_val))
                except Exception:
                    out_parts.append("?")
            else:
                out_parts.append(tok)
        return "".join(out_parts)

    def validate_token_ids(self, token_tensor: np.ndarray) -> bool:
        """
        P0 Requirement: Validate all token IDs strictly against model vocabulary bounds.
        Raises ValueError if any index is out-of-range or negative.
        """
        min_id = int(np.min(token_tensor))
        max_id = int(np.max(token_tensor))
        if min_id < 0 or max_id >= self.vocab_size:
            raise ValueError(
                f"Token ID out-of-bounds: range is [{min_id}, {max_id}], but model vocab_size is {self.vocab_size}"
            )
        return True

    def save(self, path: Union[str, Path]):
        """Persist tokenizer vocabulary and metadata to JSON file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "model_type": "faraday_code_tokenizer",
            "vocab_size": self.vocab_size,
            "special_tokens": {
                "pad": PAD_TOKEN,
                "unk": UNK_TOKEN,
                "bos": BOS_TOKEN,
                "eos": EOS_TOKEN,
            },
            "vocab": self.vocab
        }
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Union[str, Path]) -> "CodeTokenizer":
        """Load tokenizer from JSON configuration file."""
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"Tokenizer config not found at: {target}")
        data = json.loads(target.read_text(encoding="utf-8"))
        vocab = data.get("vocab", {})
        vocab_size = data.get("vocab_size", DEFAULT_VOCAB_SIZE)
        return cls(vocab=vocab, vocab_size=vocab_size)

    @classmethod
    def get_default(cls, config_path: Optional[Path] = None) -> "CodeTokenizer":
        """Convenience loader: loads persisted tokenizer.json or creates and saves default."""
        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent.parent / "models" / "onnx" / "tokenizer.json"

        if config_path.exists():
            try:
                return cls.load(config_path)
            except Exception:
                pass

        tok = cls(vocab_size=DEFAULT_VOCAB_SIZE)
        try:
            tok.save(config_path)
        except Exception:
            pass
        return tok
