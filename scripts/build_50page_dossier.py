"""
build_50page_dossier.py
Generates the comprehensive 50-page Faraday Technical Documentary Dossier.
Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import sys
import subprocess
from pathlib import Path
import pypdf

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "submission_docs"
DOCS_DIR.mkdir(exist_ok=True)
HTML_PATH = DOCS_DIR / "Faraday_Documentary.html"
PDF_PATH = DOCS_DIR / "Faraday_Complete_Documentary_Dossier.pdf"
SUBMISSION_PDF_PATH = DOCS_DIR / "Faraday_Project_Submission.pdf"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CSS_STYLES = '''
@page {
    size: A4 portrait;
    margin: 12mm 14mm 12mm 14mm;
}

* {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    background: #ffffff;
    line-height: 1.38;
    font-size: 8.8pt;
    margin: 0;
    padding: 0;
}

.page-container {
    width: 100%;
    min-height: 268mm;
    max-height: 271mm;
    page-break-after: always;
    page-break-inside: avoid;
    position: relative;
    padding-bottom: 8mm;
    overflow: hidden;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1.5px solid #0284c7;
    padding-bottom: 2.5mm;
    margin-bottom: 3.5mm;
    font-size: 7.5pt;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.page-header .brand {
    color: #0369a1;
    font-weight: 800;
}

.page-footer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #cbd5e1;
    padding-top: 2mm;
    font-size: 7.5pt;
    color: #94a3b8;
}

.page-footer .author {
    color: #475569;
    font-weight: 600;
}

h1 {
    font-size: 15pt;
    color: #0f172a;
    margin: 0 0 3mm 0;
    font-weight: 800;
    letter-spacing: -0.3px;
    line-height: 1.2;
}

h2 {
    font-size: 11pt;
    color: #0369a1;
    margin: 3mm 0 2mm 0;
    font-weight: 700;
    letter-spacing: -0.2px;
    line-height: 1.2;
}

h3 {
    font-size: 9.5pt;
    color: #0f172a;
    margin: 2mm 0 1.5mm 0;
    font-weight: 700;
}

p {
    margin: 0 0 2.2mm 0;
    text-align: justify;
}

ul, ol {
    margin: 0 0 2.2mm 0;
    padding-left: 5mm;
}

li {
    margin-bottom: 1mm;
}

.pillar-tag {
    display: inline-block;
    background: #e0f2fe;
    color: #0369a1;
    font-weight: 700;
    font-size: 7.2pt;
    padding: 1px 6px;
    border-radius: 3px;
    border: 1px solid #bae6fd;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-bottom: 2mm;
}

.highlight-box {
    background: #f8fafc;
    border-left: 3.5px solid #0284c7;
    padding: 2.5mm 3.5mm;
    margin: 2mm 0 2.5mm 0;
    border-radius: 0 4px 4px 0;
    border-top: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    font-size: 8.5pt;
}

.highlight-box strong {
    color: #0f172a;
}

.alert-danger {
    background: #fef2f2;
    border-left: 3.5px solid #ef4444;
    padding: 2.5mm 3.5mm;
    margin: 2mm 0 2.5mm 0;
    border-radius: 0 4px 4px 0;
    border-top: 1px solid #fee2e2;
    border-right: 1px solid #fee2e2;
    border-bottom: 1px solid #fee2e2;
    font-size: 8.5pt;
}

.alert-success {
    background: #f0fdf4;
    border-left: 3.5px solid #22c55e;
    padding: 2.5mm 3.5mm;
    margin: 2mm 0 2.5mm 0;
    border-radius: 0 4px 4px 0;
    border-top: 1px solid #dcfce7;
    border-right: 1px solid #dcfce7;
    border-bottom: 1px solid #dcfce7;
    font-size: 8.5pt;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 2mm 0 2.5mm 0;
    font-size: 8pt;
}

th {
    background: #0f172a;
    color: #ffffff;
    padding: 2mm 2.5mm;
    text-align: left;
    font-weight: 700;
    border: 1px solid #334155;
}

td {
    padding: 1.8mm 2.5mm;
    border: 1px solid #cbd5e1;
    vertical-align: top;
}

tr:nth-child(even) td {
    background: #f8fafc;
}

pre {
    background: #0f172a;
    color: #f8fafc;
    padding: 2.5mm 3mm;
    border-radius: 4px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 7.6pt;
    line-height: 1.32;
    margin: 2mm 0 2.5mm 0;
    border: 1px solid #1e293b;
    overflow: hidden;
    white-space: pre-wrap;
    word-break: break-all;
}

code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8pt;
    background: #f1f5f9;
    color: #0f172a;
    padding: 1px 3px;
    border-radius: 2px;
    border: 1px solid #e2e8f0;
}

.cover-title {
    font-size: 28pt;
    font-weight: 900;
    color: #0f172a;
    letter-spacing: -0.5px;
    margin-bottom: 2mm;
    line-height: 1.1;
}

.cover-subtitle {
    font-size: 13pt;
    font-weight: 600;
    color: #0284c7;
    margin-bottom: 6mm;
    line-height: 1.3;
}

.meta-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 3mm;
    margin: 4mm 0;
}

.meta-card {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 3mm;
}

.meta-card .label {
    font-size: 7pt;
    color: #64748b;
    text-transform: uppercase;
    font-weight: 700;
}

.meta-card .value {
    font-size: 9pt;
    color: #0f172a;
    font-weight: 700;
    margin-top: 1mm;
}
'''

def write_page(f, page_num, header_title, content_html):
    f.write(f'''
    <div class="page-container">
        <div class="page-header">
            <span class="brand">FARADAY // ON-DEVICE AI COPILOT</span>
            <span>{header_title}</span>
            <span>PAGE {page_num:02d} / 50</span>
        </div>
        <div class="page-body">
            {content_html}
        </div>
        <div class="page-footer">
            <span class="author">Author: Monishwaran K | Qualcomm Snapdragon Innovation Challenge 2026</span>
            <span>Confidential Architectural Dossier | 100% Air-Gapped Zero Data Egress</span>
            <span>Page {page_num}</span>
        </div>
    </div>
    ''')

print("Generator functions defined.")
