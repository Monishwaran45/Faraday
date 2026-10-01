"""
finding.py

Unified, structured security finding data model for Faraday.
Standardizes findings across Static Analysis, AST Taint Tracking,
Qualcomm NPU Neural Classification, and AI Code Review.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from backend.core.cwe_catalog import lookup_taxonomy


@dataclass
class SecurityFinding:
    """
    Standardized, confidence-scored security finding model.
    Follows SARIF v2.1.0 and enterprise compliance schemas.
    """
    rule_id: str = "SEC-GEN01"
    cwe: str = "CWE-1000"
    owasp: str = "A00:2021-Security-Misconfiguration"
    severity: str = "HIGH"
    confidence: float = 0.95
    source: str = "STATIC"
    file_path: str = ""
    line_number: int = 1
    evidence: str = ""
    explanation: str = ""
    remediation: str = ""
    _label: Optional[str] = None
    _snippet: Optional[str] = None

    def __init__(
        self,
        rule_id: Optional[str] = None,
        cwe: Optional[str] = None,
        owasp: Optional[str] = None,
        severity: str = "HIGH",
        confidence: Optional[float] = None,
        source: str = "STATIC",
        file_path: str = "",
        line_number: int = 1,
        evidence: Optional[str] = None,
        explanation: Optional[str] = None,
        remediation: Optional[str] = None,
        label: Optional[str] = None,
        snippet: Optional[str] = None,
    ):
        lbl = label or explanation or "Security Finding"
        tax = lookup_taxonomy(lbl)

        self.file_path = file_path
        self.line_number = line_number
        self.severity = severity.capitalize() if severity else tax.default_severity
        self.rule_id = rule_id or tax.rule_id
        self.cwe = cwe or tax.cwe
        self.owasp = owasp or tax.owasp
        self.confidence = confidence if confidence is not None else tax.default_confidence
        self.source = source
        self.evidence = evidence if evidence is not None else (snippet or "")
        self.explanation = explanation if explanation is not None else (f"{lbl}: {tax.description}" if label else tax.description)
        self.remediation = remediation if remediation is not None else tax.remediation
        self._label = label
        self._snippet = snippet

    # Backwards-compatibility properties with legacy SecretFinding
    @property
    def label(self) -> str:
        return self._label or self.explanation

    @property
    def snippet(self) -> str:
        return self._snippet or self.evidence

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_static(
        cls,
        label: str,
        severity: str,
        file_path: str,
        line_number: int,
        snippet: str,
        confidence: Optional[float] = None
    ) -> "SecurityFinding":
        tax = lookup_taxonomy(label)
        return cls(
            rule_id=tax.rule_id,
            cwe=tax.cwe,
            owasp=tax.owasp,
            severity=severity.capitalize(),
            confidence=confidence if confidence is not None else tax.default_confidence,
            source="STATIC",
            file_path=file_path,
            line_number=line_number,
            evidence=snippet,
            explanation=f"{label}: {tax.description}",
            remediation=tax.remediation
        )

    @classmethod
    def from_ast_taint(
        cls,
        rule_id: str,
        file_path: str,
        line_number: int,
        source_name: str,
        sink_name: str,
        evidence: str
    ) -> "SecurityFinding":
        tax = lookup_taxonomy(rule_id)
        return cls(
            rule_id=tax.rule_id,
            cwe=tax.cwe,
            owasp=tax.owasp,
            severity=tax.default_severity,
            confidence=0.96,  # AST taint proofs have very high confidence
            source="AST_TAINT",
            file_path=file_path,
            line_number=line_number,
            evidence=evidence,
            explanation=(
                f"Data-flow taint analysis detected untrusted input from source '{source_name}' "
                f"propagating directly into critical sink '{sink_name}' without sanitization."
            ),
            remediation=tax.remediation
        )

    @classmethod
    def from_ai_classifier(
        cls,
        cwe: str,
        severity: str,
        confidence: float,
        file_path: str,
        line_number: int,
        evidence: str,
        explanation: str,
        remediation: str
    ) -> "SecurityFinding":
        tax = lookup_taxonomy(cwe)
        return cls(
            rule_id=tax.rule_id,
            cwe=tax.cwe,
            owasp=tax.owasp,
            severity=severity.upper(),
            confidence=round(confidence, 2),
            source="AI_CLASSIFIER",
            file_path=file_path,
            line_number=line_number,
            evidence=evidence,
            explanation=explanation,
            remediation=remediation
        )
