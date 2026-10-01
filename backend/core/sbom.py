"""
sbom.py

Software Bill of Materials (SBOM) generator for Faraday.
Complies with Executive Order 14028 and enterprise supply chain compliance.
Supports:
1. CycloneDX v1.5 JSON schema
2. SPDX v2.3 JSON schema

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
import importlib.metadata


def get_installed_dependencies() -> List[Dict[str, Any]]:
    """Discovers installed packages and dependencies in the active Python environment."""
    components = []
    # Core project identity
    components.append({
        "name": "faraday",
        "version": "1.0.1",
        "description": "Air-Gapped AI Code Assurance & Security Copilot on Qualcomm Snapdragon Hexagon NPU",
        "license": "Apache-2.0",
        "purl": "pkg:pypi/faraday@1.0.1",
        "supplier": "Monishwaran K",
        "scope": "required",
    })

    target_packages = [
        "onnxruntime", "torch", "numpy", "rich", "pyyaml", "pytest", "anyio"
    ]
    for pkg in target_packages:
        try:
            dist = importlib.metadata.distribution(pkg)
            version = dist.version
            meta = dist.metadata
            license_val = meta.get("License", "Proprietary/Open-Source")
            components.append({
                "name": pkg,
                "version": version,
                "description": meta.get("Summary", f"{pkg} dependency for Faraday"),
                "license": license_val,
                "purl": f"pkg:pypi/{pkg}@{version}",
                "supplier": meta.get("Author", "PyPI Maintainers"),
                "scope": "required",
            })
        except Exception:
            pass

    return components


def generate_cyclonedx_sbom(components: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Generates CycloneDX v1.5 JSON SBOM document."""
    if components is None:
        components = get_installed_dependencies()

    doc = {
        "$schema": "http://cyclonedx.org/schema/bom-1.5.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "name": "faraday",
                "version": "1.0.1",
                "type": "application",
                "description": "Air-Gapped AI Code Assurance & Security Copilot on Qualcomm Snapdragon Hexagon NPU",
            },
            "tools": [
                {
                    "vendor": "Qualcomm Snapdragon Innovation Challenge",
                    "name": "Faraday SBOM Generator",
                    "version": "1.0.1"
                }
            ]
        },
        "components": [
            {
                "type": "library" if c["name"] != "faraday" else "application",
                "name": c["name"],
                "version": c["version"],
                "description": c.get("description", ""),
                "purl": c.get("purl", f"pkg:pypi/{c['name']}@{c['version']}"),
                "licenses": [
                    {
                        "license": {
                            "name": c.get("license", "Unknown")
                        }
                    }
                ]
            }
            for c in components
        ]
    }
    return doc


def generate_spdx_sbom(components: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Generates SPDX v2.3 JSON SBOM document."""
    if components is None:
        components = get_installed_dependencies()

    packages = []
    for c in components:
        packages.append({
            "SPDXID": f"SPDXRef-Package-{c['name'].replace('_', '-')}",
            "name": c["name"],
            "versionInfo": c["version"],
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": c.get("license", "NOASSERTION"),
            "licenseDeclared": c.get("license", "NOASSERTION"),
            "copyrightText": f"Copyright (c) {c.get('supplier', 'Contributors')}",
            "description": c.get("description", ""),
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": c.get("purl", f"pkg:pypi/{c['name']}@{c['version']}")
                }
            ]
        })

    doc = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "Faraday-Software-Bill-of-Materials",
        "documentNamespace": "https://github.com/Monishwaran45/Faraday/spdx/1.0.1",
        "creationInfo": {
            "creators": ["Tool: Faraday-1.0.1", "Person: Monishwaran K"],
            "created": "2026-10-01T20:00:00Z"
        },
        "packages": packages
    }
    return doc


def export_sbom(format_type: str = "cyclonedx", output_path: Optional[Path] = None) -> Path:
    """Exports SBOM to specified JSON file path."""
    fmt = format_type.lower().strip()
    if fmt in ("cyclonedx", "cdx"):
        doc = generate_cyclonedx_sbom()
        default_name = "faraday_bom.cyclonedx.json"
    elif fmt in ("spdx", "spdx-json"):
        doc = generate_spdx_sbom()
        default_name = "faraday_bom.spdx.json"
    else:
        raise ValueError(f"Unsupported SBOM format '{format_type}'. Use 'cyclonedx' or 'spdx'.")

    target = output_path or Path("review_output") / default_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return target
