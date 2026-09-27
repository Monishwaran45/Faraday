"""
sarif_builder.py

Generates OASIS SARIF v2.1.0 output for enterprise CI/CD systems:
- GitHub Advanced Security & Code Scanning tab
- GitLab SAST Reports
- Azure DevOps Pipelines
- VS Code SARIF Viewer
"""

import json
from pathlib import Path
from typing import Any, Dict, List


def severity_to_sarif_level(severity: str) -> str:
    s = (severity or "").upper()
    if s == "HIGH":
        return "error"
    elif s == "MEDIUM":
        return "warning"
    else:
        return "note"


def generate_sarif_report(
    secret_findings: List[Any],
    chunk_reviews: List[Any],
    repo_root: Path,
) -> Dict[str, Any]:
    """Build OASIS SARIF v2.1.0 document from Faraday findings."""
    rules_dict: Dict[str, Dict[str, Any]] = {}
    results = []

    CWE_MAP = {
        "xss": ("CWE-79", "https://cwe.mitre.org/data/definitions/79.html"),
        "sql": ("CWE-89", "https://cwe.mitre.org/data/definitions/89.html"),
        "key": ("CWE-798", "https://cwe.mitre.org/data/definitions/798.html"),
        "password": ("CWE-798", "https://cwe.mitre.org/data/definitions/798.html"),
        "secret": ("CWE-798", "https://cwe.mitre.org/data/definitions/798.html"),
        "token": ("CWE-798", "https://cwe.mitre.org/data/definitions/798.html"),
        "eval": ("CWE-94", "https://cwe.mitre.org/data/definitions/94.html"),
        "exec": ("CWE-94", "https://cwe.mitre.org/data/definitions/94.html"),
        "shell": ("CWE-78", "https://cwe.mitre.org/data/definitions/78.html"),
        "deserialization": ("CWE-502", "https://cwe.mitre.org/data/definitions/502.html"),
        "ssl": ("CWE-295", "https://cwe.mitre.org/data/definitions/295.html"),
        "redos": ("CWE-1333", "https://cwe.mitre.org/data/definitions/1333.html"),
        "division": ("CWE-369", "https://cwe.mitre.org/data/definitions/369.html"),
        "zero": ("CWE-369", "https://cwe.mitre.org/data/definitions/369.html"),
        "cors": ("CWE-942", "https://cwe.mitre.org/data/definitions/942.html"),
        "random": ("CWE-330", "https://cwe.mitre.org/data/definitions/330.html"),
        "traversal": ("CWE-22", "https://cwe.mitre.org/data/definitions/22.html"),
        "except": ("CWE-396", "https://cwe.mitre.org/data/definitions/396.html"),
        "default": ("CWE-665", "https://cwe.mitre.org/data/definitions/665.html"),
        "debug": ("CWE-489", "https://cwe.mitre.org/data/definitions/489.html"),
    }

    # 1. Process Static Security Findings
    for idx, f in enumerate(secret_findings):
        rule_id = f"FD-SEC-{abs(hash(f.label)) % 10000:04d}"
        cwe_id, help_uri = "CWE-1000", "https://cwe.mitre.org/"
        tags = ["security", "static-analysis", "compliance"]
        for key, (cid, uri) in CWE_MAP.items():
            if key in f.label.lower():
                cwe_id = cid
                help_uri = uri
                tags.extend([cid, "OWASP-Top10"])
                break

        if rule_id not in rules_dict:
            rules_dict[rule_id] = {
                "id": rule_id,
                "name": f.label.replace(" ", ""),
                "shortDescription": {"text": f.label},
                "fullDescription": {"text": f"Faraday detected {f.label} ({cwe_id}) in source code."},
                "helpUri": help_uri,
                "help": {"text": f"Security guidance and remediation for {cwe_id}: {help_uri}"},
                "defaultConfiguration": {
                    "level": severity_to_sarif_level(f.severity),
                },
                "properties": {
                    "tags": tags,
                    "cwe": [cwe_id],
                },
            }

        # Normalize file URI relative to repo root
        try:
            rel_file = str(Path(f.file_path).relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            rel_file = Path(f.file_path).name

        results.append({
            "ruleId": rule_id,
            "level": severity_to_sarif_level(f.severity),
            "message": {
                "text": f"{f.label} [{cwe_id}]: Detected unsafe pattern in {rel_file}",
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": rel_file,
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": {
                            "startLine": max(1, f.line_number),
                            "snippet": {
                                "text": f.snippet,
                            },
                        },
                    },
                }
            ],
        })

    # 2. Process AI Code Review findings (if any contain detected issues)
    for r in chunk_reviews:
        if "ISSUES:" in r.review_raw and "None found" not in r.review_raw:
            rule_id = "FD-AI-REV"
            # Parse dynamic severity from review
            ai_level = "warning"
            if "SEVERITY:" in r.review_raw:
                after_sev = r.review_raw.split("SEVERITY:", 1)[1].splitlines()
                for s_line in after_sev:
                    s_line = s_line.strip()
                    if s_line:
                        ai_level = severity_to_sarif_level(s_line)
                        break

            if rule_id not in rules_dict:
                rules_dict[rule_id] = {
                    "id": rule_id,
                    "name": "OnDeviceAICodeReviewFinding",
                    "shortDescription": {"text": "Snapdragon On-Device AI Code Review Finding"},
                    "fullDescription": {"text": "Heuristic or neural code review detected code quality/security issues."},
                    "defaultConfiguration": {"level": "warning"},
                    "properties": {"tags": ["code-quality", "ai-review", "snapdragon-npu"]},
                }

            try:
                rel_file = str(Path(r.file_path).relative_to(repo_root)).replace("\\", "/")
            except ValueError:
                rel_file = Path(r.file_path).name

            results.append({
                "ruleId": rule_id,
                "level": ai_level,
                "message": {
                    "text": f"Code review note for {r.chunk_name}: {r.review_raw.splitlines()[0] if r.review_raw.splitlines() else 'Review issue detected'}",
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": rel_file,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {
                                "startLine": max(1, r.start_line),
                                "endLine": max(r.start_line, r.end_line),
                            },
                        },
                    }
                ],
            })

    sarif_doc = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Faraday",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/faraday-ai/faraday",
                        "rules": list(rules_dict.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return sarif_doc


def write_sarif_file(sarif_doc: Dict[str, Any], output_path: Path) -> Path:
    """Write SARIF dictionary to target JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sarif_doc, indent=2), encoding="utf-8")
    return output_path
