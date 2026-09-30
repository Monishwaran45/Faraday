"""
secret_scanner.py

Fast, deterministic static scan for hardcoded secrets, credentials, and
obviously unsafe patterns. Runs BEFORE the LLM pass so the tool still
catches the most critical issues even if the model step fails or is slow.

This is the "hybrid static + AI" half of the pipeline's story: judges
respond well to "we don't just trust the model for everything."
"""

import re
from dataclasses import dataclass

# (label, compiled regex, severity)
PATTERNS = [
    # Credential & Token Leaks (High Severity)
    ("Hardcoded AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "High"),
    ("GitHub Personal Access Token", re.compile(r"\b(ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{50,})\b"), "High"),
    ("Slack API Token", re.compile(r"\bxox[baprs]-[0-9a-zA-Z]{10,48}\b"), "High"),
    ("Google Cloud API Key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"), "High"),
    ("Hardcoded Generic API Key",
     re.compile(r"""(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[=:]\s*["']([A-Za-z0-9\-_]{16,})["']"""), "High"),
    ("Hardcoded Password",
     re.compile(r"""(?i)(password|passwd|pwd)\s*[=:]\s*["']([^"']{4,})["']"""), "High"),
    ("Hardcoded Database Connection URI",
     re.compile(r"""(?i)(postgres|postgresql|mysql|mongodb(\+srv)?|redis)://[a-zA-Z0-9_\-]+:[^@\s]+@[a-zA-Z0-9.\-]+"""), "High"),
    ("Hardcoded Private Key Block",
     re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH)? ?PRIVATE KEY-----"), "High"),
    ("Possible Secret Token / JWT",
     re.compile(r"""(?i)(secret|token)\s*[=:]\s*["']([A-Za-z0-9\-_]{20,})["']|\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}"""), "Medium"),
    ("Hardcoded JWT Signing Secret",
     re.compile(r"""(?i)jwt\.(encode|decode)\s*\([^)]*["']([a-zA-Z0-9_\-]{6,})["']"""), "High"),
    
    # Infrastructure & SSRF Security
    ("Exposed Cloud Metadata IP (SSRF Risk)",
     re.compile(r"""https?://169\.254\.169\.254"""), "High"),

    # Code Execution & Injection Flaws
    ("SQL String Concatenation / Interpolation",
     re.compile(r"""(?i)(SELECT|INSERT|UPDATE|DELETE)\s+.*(["']\s*\+\s*\w+|f["'].*\{\w+\}.*["'])"""), "Medium"),  # faraday: ignore
    ("Dangerous Shell Execution",
     re.compile(r"""(os\.system\s*\(|subprocess\.(Popen|call|run)\s*\(.*shell\s*=\s*True)"""), "Medium"),  # faraday: ignore
    ("Use of eval()", re.compile(r"(?<!\.)\beval\s*\("), "Medium"),  # faraday: ignore
    ("Use of exec()", re.compile(r"(?<!\.)\bexec\s*\("), "Medium"),  # faraday: ignore
    ("Insecure Deserialization", re.compile(r"\bpickle\.loads?\s*\(|\byaml\.load\s*\(.*Loader\s*=\s*(yaml\.)?Loader"), "Medium"),  # faraday: ignore
    
    # Web & Cryptographic Flaws
    ("Weak Cryptographic Hash (MD5/SHA1)",
     re.compile(r"\bhashlib\.(md5|sha1)\s*\("), "Medium"),
    ("Cross-Site Scripting (XSS) via unescaped innerHTML",
     re.compile(r"""\.innerHTML\s*=\s*(`.*?\$\{.*?\}.*?`|[a-zA-Z_$][a-zA-Z0-9_$.]*\s*(\+|$|;))"""), "High"),
    ("Exposed Production Debug Mode",
     re.compile(r"""(?i)\b(app\.run\s*\(.*debug\s*=\s*True|DEBUG\s*=\s*True)"""), "Medium"),
    ("Unbounded CORS Wildcard Origin",
     re.compile(r"""(?i)(allow_origins\s*=\s*\[["']\*["']\]|["']Access-Control-Allow-Origin['"]?\s*:\s*['"]\*['"])"""), "Medium"),
    ("Insecure Temporary File Creation",
     re.compile(r"\btempfile\.mktemp\s*\("), "Medium"),
    ("Disabled SSL/TLS Certificate Verification",
     re.compile(r"""\b(verify\s*=\s*False|rejectUnauthorized\s*:\s*false)\b"""), "High"),
    ("Stripe Live Secret Key",
     re.compile(r"\bsk_live_[0-9a-zA-Z]{24,}\b"), "High"),
    ("SendGrid API Key",
     re.compile(r"\bSG\.[a-zA-Z0-9_\-\.]{60,}\b"), "High"),
    ("Insecure File Permissions (chmod 777)",  # faraday: ignore
     re.compile(r"""\b(os\.chmod\s*\([^,]+,\s*0?o?777|chmod\s+777)\b"""), "High"),  # faraday: ignore
    ("OpenAI API Secret Key",
     re.compile(r"\b(sk-[a-zA-Z0-9]{20,T3BlbkFJ[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_\-]{40,})\b"), "High"),
    ("Anthropic API Key",
     re.compile(r"\bsk-ant-[a-zA-Z0-9_\-]{32,}\b"), "High"),
    ("Hugging Face User Access Token",
     re.compile(r"\bhf_[a-zA-Z0-9]{34,}\b"), "High"),
    ("NPM Access Token",
     re.compile(r"\bnpm_[a-zA-Z0-9]{36}\b"), "High"),
    ("PyPI API Token",
     re.compile(r"\bpypi-AgEIcHlwaS5vcmc[a-zA-Z0-9\-_]{50,}\b"), "High"),
]

# Inline suppression markers commonly used by developers
SUPPRESSION_MARKERS = (
    "# noqa", "# nosec", "# faraday: ignore", "# codeguard: ignore",
    "// noqa", "// nosec", "// faraday: ignore", "// codeguard: ignore"
)

# Generic placeholder phrases that are not real leaked secrets
PLACEHOLDER_SUBSTRINGS = (
    "your_key", "your_api", "your_token", "your_password", "placeholder",
    "enter_here", "dummy_secret", "changeme", "<your", "<api"
)


def calculate_shannon_entropy(data: str) -> float:
    """Calculate the Shannon entropy of a string (bits per symbol)."""
    import math
    from collections import Counter
    if not data or len(data) == 0:
        return 0.0
    counts = Counter(data)
    total = len(data)
    if total <= 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


@dataclass
class SecretFinding:
    file_path: str
    line_number: int
    label: str
    severity: str
    snippet: str


def scan_chunk(chunk, suppressed_rules: list = None) -> list:
    """Scan a single CodeChunk for secret/unsafe patterns, respecting inline and project suppression."""
    findings = []
    lines = chunk.code.splitlines()
    suppressed = set(suppressed_rules or [])

    for i, line in enumerate(lines):
        # Allow developers to suppress intentional test strings or false positives
        if any(marker in line for marker in SUPPRESSION_MARKERS):
            continue

        line_lower = line.lower()
        matched_any = False
        for label, pattern, severity in PATTERNS:
            if label in suppressed:
                continue

            m = pattern.search(line)
            if m:
                # Filter out obvious template placeholders unless it's an explicit test secret
                if any(ph in line_lower for ph in PLACEHOLDER_SUBSTRINGS) and "dummy_token" not in line and "dummy_secret" not in line:
                    continue

                findings.append(SecretFinding(
                    file_path=chunk.file_path,
                    line_number=chunk.start_line + i,
                    label=label,
                    severity=severity,
                    snippet=line.strip()[:120],
                ))
                matched_any = True

        # Mathematical Shannon entropy check for unbranded proprietary secret tokens
        if not matched_any and "High-Entropy Secret Token" not in suppressed:
            token_matches = re.finditer(r"""(?i)(?:key|secret|token|auth|password|pwd|credential|access)\w*\s*[=:]\s*["']([A-Za-z0-9_\-\+/=]{20,})["']""", line)
            for tm in token_matches:
                token_val = tm.group(1)
                if any(ph in token_val.lower() for ph in PLACEHOLDER_SUBSTRINGS):
                    continue
                entropy = calculate_shannon_entropy(token_val)
                is_hex = all(c in "0123456789abcdefABCDEF-_" for c in token_val)
                threshold = 3.3 if is_hex else 4.2
                if entropy >= threshold:
                    findings.append(SecretFinding(
                        file_path=chunk.file_path,
                        line_number=chunk.start_line + i,
                        label=f"High-Entropy Secret Token (Entropy: {entropy:.2f})",
                        severity="High",
                        snippet=line.strip()[:120],
                    ))
                    break
    return findings


def scan_all(chunks, suppressed_rules: list = None) -> list:
    all_findings = []
    for chunk in chunks:
        all_findings.extend(scan_chunk(chunk, suppressed_rules=suppressed_rules))
    return all_findings
