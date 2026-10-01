"""
cwe_catalog.py

Comprehensive CWE and OWASP Top 10 Taxonomy Mapping for Faraday.
Provides authoritative mapping for vulnerabilities detected across static analysis,
AST taint analysis, and on-device neural review.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from dataclasses import dataclass
from typing import Dict, Optional, List


@dataclass
class VulnerabilityTaxonomy:
    rule_id: str
    cwe: str
    cwe_title: str
    owasp: str
    default_severity: str
    default_confidence: float
    description: str
    remediation: str


CWE_CATALOG: Dict[str, VulnerabilityTaxonomy] = {
    "SEC-SQL01": VulnerabilityTaxonomy(
        rule_id="SEC-SQL01",
        cwe="CWE-89",
        cwe_title="Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')",
        owasp="A03:2021-Injection",
        default_severity="HIGH",
        default_confidence=0.95,
        description="Unsanitized untrusted input or string concatenation concatenated into an SQL query string.",
        remediation="Use parameterized queries (prepared statements) or ORM query abstractions."
    ),
    "SEC-CMD01": VulnerabilityTaxonomy(
        rule_id="SEC-CMD01",
        cwe="CWE-78",
        cwe_title="Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')",
        owasp="A03:2021-Injection",
        default_severity="HIGH",
        default_confidence=0.94,
        description="Execution of system commands via os.system or subprocess with shell=True and dynamic variables.",
        remediation="Avoid shell=True; pass command arguments as a list directly to subprocess.run(..., shell=False)."
    ),
    "SEC-XSS01": VulnerabilityTaxonomy(
        rule_id="SEC-XSS01",
        cwe="CWE-79",
        cwe_title="Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')",
        owasp="A03:2021-Injection",
        default_severity="HIGH",
        default_confidence=0.92,
        description="Unescaped dynamic data injected into DOM via .innerHTML, dangerouslySetInnerHTML, or document.write.",
        remediation="Use textContent or safe DOM templating/sanitization libraries (DOMPurify)."
    ),
    "SEC-EVAL01": VulnerabilityTaxonomy(
        rule_id="SEC-EVAL01",
        cwe="CWE-95",
        cwe_title="Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')",
        owasp="A03:2021-Injection",
        default_severity="HIGH",
        default_confidence=0.95,
        description="Execution of arbitrary untrusted strings through eval() or exec() builtins.",  # faraday: ignore
        remediation="Remove eval/exec calls; replace with safe dispatch tables or ast.literal_eval."  # faraday: ignore
    ),
    "SEC-DESER01": VulnerabilityTaxonomy(
        rule_id="SEC-DESER01",
        cwe="CWE-502",
        cwe_title="Deserialization of Untrusted Data",
        owasp="A08:2021-Software and Data Integrity Failures",
        default_severity="HIGH",
        default_confidence=0.90,
        description="Unsafe object deserialization using pickle.loads() or unvalidated yaml.load().",  # faraday: ignore
        remediation="Use safe serialization formats like JSON, or yaml.safe_load(Loader=yaml.SafeLoader)."  # faraday: ignore
    ),
    "SEC-PATH01": VulnerabilityTaxonomy(
        rule_id="SEC-PATH01",
        cwe="CWE-22",
        cwe_title="Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')",
        owasp="A01:2021-Broken Access Control",
        default_severity="HIGH",
        default_confidence=0.89,
        description="File path constructed directly from untrusted input without canonicalization or directory sandboxing.",
        remediation="Validate paths using Path.resolve() and verify the resolved path starts with the trusted base root."
    ),
    "SEC-RAND01": VulnerabilityTaxonomy(
        rule_id="SEC-RAND01",
        cwe="CWE-330",
        cwe_title="Use of Insufficiently Random Values",
        owasp="A02:2021-Cryptographic Failures",
        default_severity="HIGH",
        default_confidence=0.91,
        description="Pseudorandom generator (random.random, Math.random) used in security, token, or session contexts.",
        remediation="Use cryptographically secure generators: Python 'secrets' module or 'crypto.getRandomValues()'."
    ),
    "SEC-KEY01": VulnerabilityTaxonomy(
        rule_id="SEC-KEY01",
        cwe="CWE-798",
        cwe_title="Use of Hard-coded Credentials",
        owasp="A07:2021-Identification and Authentication Failures",
        default_severity="HIGH",
        default_confidence=0.98,
        description="Static API key, bearer token, private key, or password embedded in source code.",
        remediation="Store secrets in environment variables or an enterprise secret manager (Vault, KMS)."
    ),
    "SEC-HASH01": VulnerabilityTaxonomy(
        rule_id="SEC-HASH01",
        cwe="CWE-328",
        cwe_title="Use of Weak Hash",
        owasp="A02:2021-Cryptographic Failures",
        default_severity="MEDIUM",
        default_confidence=0.90,
        description="Collision-prone hash functions (MD5 or SHA-1) used for data integrity or security verification.",
        remediation="Upgrade to SHA-256, SHA-512, or password hashing functions (argon2, bcrypt)."
    ),
    "SEC-TLS01": VulnerabilityTaxonomy(
        rule_id="SEC-TLS01",
        cwe="CWE-295",
        cwe_title="Improper Certificate Validation",
        owasp="A07:2021-Identification and Authentication Failures",
        default_severity="HIGH",
        default_confidence=0.95,
        description="TLS/SSL certificate validation disabled (verify=False or rejectUnauthorized: false).",  # faraday: ignore
        remediation="Enforce valid certificate verification in all non-local environments."
    ),
    "SEC-DEBUG01": VulnerabilityTaxonomy(
        rule_id="SEC-DEBUG01",
        cwe="CWE-489",
        cwe_title="Active Debug Code",
        owasp="A05:2021-Security Misconfiguration",
        default_severity="MEDIUM",
        default_confidence=0.88,
        description="Application configured with active debug mode enabled in server initialization.",
        remediation="Ensure debug flags are disabled or conditionally controlled by production environment variables."
    ),
    "SEC-DIV01": VulnerabilityTaxonomy(
        rule_id="SEC-DIV01",
        cwe="CWE-369",
        cwe_title="Divide By Zero",
        owasp="A04:2021-Insecure Design",
        default_severity="MEDIUM",
        default_confidence=0.85,
        description="Mathematical division by variable denominator without explicit zero-check guard.",
        remediation="Insert an explicit guard check (e.g. 'if denominator != 0:') before division."
    ),
}


def lookup_taxonomy(label_or_rule: str) -> VulnerabilityTaxonomy:
    """Lookup taxonomy entry by rule_id or fuzzy match on label name."""
    if label_or_rule in CWE_CATALOG:
        return CWE_CATALOG[label_or_rule]

    lower = label_or_rule.lower()
    if "sql" in lower:
        return CWE_CATALOG["SEC-SQL01"]
    elif "command" in lower or "shell" in lower:
        return CWE_CATALOG["SEC-CMD01"]
    elif "xss" in lower or "innerhtml" in lower:
        return CWE_CATALOG["SEC-XSS01"]
    elif "eval" in lower or "exec" in lower:
        return CWE_CATALOG["SEC-EVAL01"]
    elif "deserial" in lower or "pickle" in lower:
        return CWE_CATALOG["SEC-DESER01"]
    elif "traversal" in lower or "path" in lower:
        return CWE_CATALOG["SEC-PATH01"]
    elif "random" in lower:
        return CWE_CATALOG["SEC-RAND01"]
    elif "key" in lower or "password" in lower or "token" in lower or "secret" in lower:
        return CWE_CATALOG["SEC-KEY01"]
    elif "md5" in lower or "sha1" in lower or "hash" in lower:
        return CWE_CATALOG["SEC-HASH01"]
    elif "ssl" in lower or "certificate" in lower or "tls" in lower:
        return CWE_CATALOG["SEC-TLS01"]
    elif "debug" in lower:
        return CWE_CATALOG["SEC-DEBUG01"]
    elif "division" in lower:
        return CWE_CATALOG["SEC-DIV01"]

    # Generic fallback
    return VulnerabilityTaxonomy(
        rule_id="SEC-GEN01",
        cwe="CWE-699",
        cwe_title="Software Development Quality & Security Flaw",
        owasp="A04:2021-Insecure Design",
        default_severity="MEDIUM",
        default_confidence=0.80,
        description="Identified potential code assurance or vulnerability issue.",
        remediation="Review code implementation against secure programming guidelines."
    )


def generate_cwe_matrix_table() -> str:
    """Generate Markdown coverage matrix for documentation and reports."""
    lines = [
        "| Rule ID | CWE | CWE Name | OWASP Top 10 (2021) | Severity | Default Confidence |",
        "|---|---|---|---|---|---|"
    ]
    for r in CWE_CATALOG.values():
        lines.append(f"| `{r.rule_id}` | `{r.cwe}` | {r.cwe_title} | `{r.owasp}` | **{r.default_severity}** | {r.default_confidence * 100:.0f}% |")
    return "\n".join(lines)
