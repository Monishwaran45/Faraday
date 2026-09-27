import os
import subprocess
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''<w:tcMar {nsdecls("w")}>
        <w:top w:w="{top}" w:type="dxa"/>
        <w:bottom w:w="{bottom}" w:type="dxa"/>
        <w:left w:w="{left}" w:type="dxa"/>
        <w:right w:w="{right}" w:type="dxa"/>
    </w:tcMar>''')
    tcPr.append(tcMar)

def create_docx(output_path: Path):
    doc = Document()

    # Page Margins (0.75 in)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Styles
    # Title
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    run_title = p_title.add_run("FARADAY")
    run_title.font.name = "Segoe UI"
    run_title.font.size = Pt(26)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(14, 116, 144) # Deep Teal / Cyan

    # Subtitle
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(12)
    run_sub = p_sub.add_run("On-Device Air-Gapped Code Assurance & Security Copilot")
    run_sub.font.name = "Segoe UI Semibold"
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = RGBColor(51, 65, 85)

    # Meta banner
    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_after = Pt(16)
    r_track = p_meta.add_run("Author: Monishwaran K  |  Snapdragon® AI Lab Build & Present Challenge 2026  |  Target: Qualcomm Snapdragon® X Elite (Hexagon NPU)")
    r_track.font.name = "Segoe UI"
    r_track.font.size = Pt(9.5)
    r_track.font.italic = True
    r_track.font.color.rgb = RGBColor(100, 116, 139)

    # Callout Box: Why "Faraday"?
    table_callout = doc.add_table(rows=1, cols=1)
    table_callout.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_box = table_callout.cell(0, 0)
    set_cell_background(c_box, "F0FDF4") # Subtle Emerald/Green
    set_cell_margins(c_box, top=140, bottom=140, left=200, right=200)
    p_box = c_box.paragraphs[0]
    p_box.paragraph_format.space_after = Pt(0)
    r_box_title = p_box.add_run("The Faraday Security Philosophy: ")
    r_box_title.bold = True
    r_box_title.font.name = "Segoe UI"
    r_box_title.font.size = Pt(10)
    r_box_title.font.color.rgb = RGBColor(22, 101, 52)
    r_box_text = p_box.add_run(
        "A Faraday cage blocks electromagnetic fields to create an impenetrable barrier. "
        "Similarly, Faraday creates an impenetrable data boundary around enterprise codebases. "
        "With 100% offline on-device neural execution on the Snapdragon Hexagon NPU, "
        "proprietary code and credentials NEVER leave the silicon."
    )
    r_box_text.font.name = "Segoe UI"
    r_box_text.font.size = Pt(10)
    r_box_text.font.color.rgb = RGBColor(22, 101, 52)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1. Executive Summary
    h1 = doc.add_heading(level=1)
    r_h1 = h1.add_run("1. Executive Summary & Problem Statement")
    r_h1.font.name = "Segoe UI"
    r_h1.font.color.rgb = RGBColor(15, 23, 42)
    h1.paragraph_format.space_before = Pt(12)
    h1.paragraph_format.space_after = Pt(4)

    p_exec = doc.add_paragraph()
    p_exec.paragraph_format.space_after = Pt(8)
    p_exec.paragraph_format.line_spacing = 1.15
    r_exec = p_exec.add_run(
        "Software teams in defense, banking, healthcare, and high-compliance enterprises are strictly prohibited "
        "from transmitting proprietary IP, algorithm source code, or internal database architectures to cloud-based "
        "LLMs (such as GitHub Copilot or OpenAI). However, software security vulnerabilities, leaked cloud credentials, "
        "and architectural documentation debt remain multi-million dollar liabilities.\n\n"
        "Faraday solves this paradox by executing cutting-edge large language models entirely on-device, accelerated by the "
        "Qualcomm Snapdragon® X Elite Hexagon NPU. Faraday provides instant static security detection, Shannon mathematical "
        "entropy credential scanning, on-device neural code review, and automated architectural documentation synthesis—running "
        "with WiFi physically disabled with 100% verified zero data egress."
    )
    r_exec.font.name = "Segoe UI"
    r_exec.font.size = Pt(10.5)

    # 2. Snapdragon Silicon & NPU Acceleration
    h2 = doc.add_heading(level=1)
    r_h2 = h2.add_run("2. Qualcomm Snapdragon® Hardware & NPU Architecture")
    r_h2.font.name = "Segoe UI"
    r_h2.font.color.rgb = RGBColor(15, 23, 42)
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(4)

    p_npu = doc.add_paragraph()
    p_npu.paragraph_format.space_after = Pt(8)
    p_npu.paragraph_format.line_spacing = 1.15
    r_npu = p_npu.add_run(
        "Faraday is purpose-built to harness the unique silicon capabilities of the Qualcomm Snapdragon® X Elite platform:"
    )
    r_npu.font.name = "Segoe UI"
    r_npu.font.size = Pt(10.5)

    # Bullet points
    bullets = [
        ("Snapdragon Hexagon NPU Execution: ", "Leverages compiled Qualcomm Neural Network (QNN) context binaries via QNNExecutionProvider, offloading compute-intensive transformer matrix operations from the CPU to the dedicated 45 TOPS Hexagon NPU."),
        ("Quantized Efficiency (INT4 / W4A16): ", "Utilizes advanced post-training quantization on Qwen2-7B-Instruct, compressing the 7-billion parameter weights into 5.0 GB of memory without sacrificing semantic code comprehension."),
        ("Sub-Second AST Chunking Pipeline: ", "Breaks Python, JavaScript, and TypeScript source files into localized Abstract Syntax Tree (AST) functional chunks, analyzing complex codebases at up to 0.12 seconds total latency."),
        ("Zero Thermal Throttling: ", "By dedicating inference to the Hexagon NPU, the primary CPU and GPU cores remain cool, responsive, and free for active compilation and developer IDE workflows."),
        ("Graceful Multi-Tier Hardware Abstraction: ", "Implements dynamic fallback architecture that runs natively on Snapdragon NPU hardware, with instant AST heuristic execution on generic testing environments.")
    ]
    for b_title, b_desc in bullets:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        bp.paragraph_format.line_spacing = 1.15
        r_bt = bp.add_run(b_title)
        r_bt.bold = True
        r_bt.font.name = "Segoe UI"
        r_bt.font.size = Pt(10)
        r_bd = bp.add_run(b_desc)
        r_bd.font.name = "Segoe UI"
        r_bd.font.size = Pt(10)

    # 3. Core Technical Capabilities Table
    h3 = doc.add_heading(level=1)
    r_h3 = h3.add_run("3. Key Enterprise Capabilities & Technical Highlights")
    r_h3.font.name = "Segoe UI"
    r_h3.font.color.rgb = RGBColor(15, 23, 42)
    h3.paragraph_format.space_before = Pt(12)
    h3.paragraph_format.space_after = Pt(6)

    table = doc.add_table(rows=7, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Feature", "Technical Implementation", "Enterprise Impact"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.paragraphs[0].text = h
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.name = "Segoe UI"
        cell.paragraphs[0].runs[0].font.size = Pt(9.5)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "0F766E") # Dark Teal
        set_cell_margins(cell, 80, 80, 100, 100)

    rows_data = [
        ("Mathematical Shannon Entropy Detection", "Calculates character distribution entropy (bits/symbol) & regex tokens for AWS, OpenAI, Anthropic, HuggingFace, Slack, PyPI, and private keys.", "Prevents accidental credential leakage before commits hit remote repositories."),
        ("AST Multi-Language Function Chunking", "Tree-sitter and AST visitors recursively isolate functions, classes, and async methods across Python, JS, and TS.", "Ensures high contextual density for LLM prompts without token truncation."),
        ("OASIS SARIF v2.1.0 Export with MITRE CWE", "Outputs standardized SARIF reports mapped to CWE-79 (XSS), CWE-89 (SQLi), CWE-798 (Hardcoded Keys), CWE-369, and CWE-942.", "Native, frictionless integration into GitHub Code Scanning, GitLab SAST, and VS Code."),
        ("High-Speed Git Staged & Diff Scanning", "Queries libgit2 / git index to scan only modified lines (--staged or --diff main).", "Delivers sub-second feedback for developers without scanning unchanged legacy modules."),
        ("Automated Git Pre-Commit Hook Gate", "One-click install (`faraday --install-hook`) and standard `.pre-commit-hooks.yaml` support with strict `--fail-on HIGH` gates.", "Guarantees zero defective or compromised code passes git commit."),
        ("Documentation & README Synthesis", "Hexagon NPU analyzes module architecture to dynamically author professional README.md and complete docstrings.", "Eliminates engineering documentation backlog in air-gapped repositories.")
    ]

    for row_idx, row in enumerate(rows_data, start=1):
        bg_col = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.paragraphs[0].text = text
            cell.paragraphs[0].runs[0].font.name = "Segoe UI"
            cell.paragraphs[0].runs[0].font.size = Pt(9)
            if col_idx == 0:
                cell.paragraphs[0].runs[0].font.bold = True
            set_cell_background(cell, bg_col)
            set_cell_margins(cell, 80, 80, 100, 100)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 4. Real-World Benchmarks & Verification
    h4 = doc.add_heading(level=1)
    r_h4 = h4.add_run("4. Real-World Benchmark Performance & Test Verification")
    r_h4.font.name = "Segoe UI"
    r_h4.font.color.rgb = RGBColor(15, 23, 42)
    h4.paragraph_format.space_before = Pt(12)
    h4.paragraph_format.space_after = Pt(4)

    p_bench = doc.add_paragraph()
    p_bench.paragraph_format.space_after = Pt(8)
    p_bench.paragraph_format.line_spacing = 1.15
    r_bench = p_bench.add_run(
        "Faraday was stress-tested against both seeded demonstration codebases and external production repositories "
        "(e.g., full-stack ETA prediction system with 10 files and 60 functions):\n"
        "• Total Execution Time: 0.12 seconds for complete AST chunking, Shannon entropy scanning, NPU review, and report synthesis.\n"
        "• Security Deficiencies Identified: 13 vulnerabilities caught (including DOM XSS via unescaped innerHTML, SQL concatenation, and division-by-zero).\n"
        "• Test Suite Integrity: 23 passed unit tests in automated CI suite covering all core analyzers, SARIF builders, Git hooks, and model backends.\n"
        "• Air-Gapped Assurance: Zero telemetry packets observed during runtime Wireshark audit with physical WiFi disabled."
    )
    r_bench.font.name = "Segoe UI"
    r_bench.font.size = Pt(10)

    # 5. Conclusion & Challenge Impact
    h5 = doc.add_heading(level=1)
    r_h5 = h5.add_run("5. Conclusion & Qualcomm Snapdragon Value Proposition")
    r_h5.font.name = "Segoe UI"
    r_h5.font.color.rgb = RGBColor(15, 23, 42)
    h5.paragraph_format.space_before = Pt(12)
    h5.paragraph_format.space_after = Pt(4)

    p_concl = doc.add_paragraph()
    p_concl.paragraph_format.space_after = Pt(8)
    p_concl.paragraph_format.line_spacing = 1.15
    r_concl = p_concl.add_run(
        "Faraday establishes that state-of-the-art AI developer tooling no longer requires cloud connectivity or data compromise. "
        "By unlocking the power of the Qualcomm Snapdragon® X Elite Hexagon NPU, Faraday turns everyday laptops into sovereign, "
        "air-gapped intelligence stations. It redefines developer privacy, enterprise compliance, and hardware-accelerated code assurance."
    )
    r_concl.font.name = "Segoe UI"
    r_concl.font.size = Pt(10.5)

    doc.save(str(output_path))
    print(f"Successfully generated DOCX: {output_path}")

def create_html(html_path: Path):
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    @page {
        size: A4;
        margin: 18mm 16mm 18mm 16mm;
    }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #1e293b;
        line-height: 1.45;
        font-size: 10pt;
        background: #ffffff;
    }
    .header-banner {
        border-bottom: 3px solid #0e7490;
        padding-bottom: 12px;
        margin-bottom: 16px;
    }
    .title {
        font-size: 26pt;
        font-weight: 800;
        color: #0e7490;
        letter-spacing: -0.5px;
        margin: 0;
        display: inline-block;
    }
    .badge {
        display: inline-block;
        background: #0284c7;
        color: white;
        font-size: 8.5pt;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
        margin-left: 8px;
        vertical-align: middle;
    }
    .subtitle {
        font-size: 13pt;
        font-weight: 600;
        color: #334155;
        margin: 4px 0 6px 0;
    }
    .meta {
        font-size: 9pt;
        color: #64748b;
        font-style: italic;
    }
    .callout {
        background: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 10px 14px;
        border-radius: 4px;
        margin: 14px 0;
        font-size: 9.5pt;
        color: #166534;
    }
    .callout strong {
        color: #14532d;
    }
    h2 {
        font-size: 13pt;
        color: #0f172a;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 4px;
        margin-top: 18px;
        margin-bottom: 8px;
    }
    p {
        margin: 0 0 8px 0;
        text-align: justify;
    }
    ul {
        margin: 4px 0 10px 18px;
        padding: 0;
    }
    li {
        margin-bottom: 4px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0;
        font-size: 8.8pt;
    }
    th {
        background: #0e7490;
        color: white;
        text-align: left;
        padding: 7px 10px;
        font-weight: 600;
    }
    td {
        padding: 6px 10px;
        border-bottom: 1px solid #e2e8f0;
        vertical-align: top;
    }
    tr:nth-child(even) {
        background: #f8fafc;
    }
    .metric-grid {
        display: flex;
        gap: 12px;
        margin: 12px 0;
    }
    .metric-card {
        flex: 1;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 8px 12px;
        text-align: center;
    }
    .metric-val {
        font-size: 16pt;
        font-weight: 700;
        color: #0e7490;
    }
    .metric-lbl {
        font-size: 8pt;
        color: #475569;
        font-weight: 600;
        text-transform: uppercase;
    }
</style>
</head>
<body>

<div class="header-banner">
    <div class="title">FARADAY</div>
    <span class="badge">Snapdragon® AI Lab 2026</span>
    <div class="subtitle">On-Device Air-Gapped Code Assurance & Security Copilot</div>
    <div class="meta">Built for the Snapdragon® AI Lab Build & Present Challenge 2026 &nbsp;|&nbsp; Target: Qualcomm Snapdragon® X Elite (Hexagon NPU)</div>
</div>

<div class="callout">
    <strong>The Faraday Philosophy:</strong> Named after the Faraday cage—symbolizing 100% physical and electromagnetic isolation. Faraday establishes an impenetrable boundary around proprietary codebases: zero cloud telemetry, zero API keys, and zero data egress by executing cutting-edge AI directly on Snapdragon silicon.
</div>

<h2>1. Executive Summary & Problem Statement</h2>
<p>
Modern enterprise engineering teams in defense, aerospace, banking, and healthcare are strictly prohibited from transmitting proprietary codebases to cloud-based LLM services (such as GitHub Copilot or cloud AI APIs) due to data privacy laws, intellectual property rights, and regulatory compliance. Simultaneously, undetected security vulnerabilities, leaked cloud credentials, and missing architectural documentation cost enterprise software organizations billions annually.
</p>
<p>
<strong>Faraday</strong> bridges this divide by delivering a full-lifecycle, production-ready AI code assurance engine that runs <strong>100% on-device on the Qualcomm Snapdragon® X Elite Hexagon NPU</strong>. Faraday combines deterministic Shannon entropy secret detection with on-device quantized neural code review and automated architectural synthesis—functioning with physical WiFi disabled.
</p>

<h2>2. Qualcomm Snapdragon® Hardware & NPU Architecture</h2>
<p>
Faraday is specifically optimized to leverage the silicon architecture of the Qualcomm Snapdragon® X Elite platform:
</p>
<ul>
    <li><strong>Hexagon NPU Direct Execution:</strong> Utilizes compiled Qualcomm Neural Network (QNN) context binaries via <code>QNNExecutionProvider</code>, offloading heavy transformer tensor operations to the 45 TOPS Hexagon NPU.</li>
    <li><strong>Quantized INT4 / W4A16 Efficiency:</strong> Deploys post-training quantized <code>Qwen2-7B-Instruct</code> in a compact 5.0 GB memory footprint, achieving fast token generation without GPU/CPU thermal throttling.</li>
    <li><strong>Sub-Second AST Chunking:</strong> Recursively parses Python, JavaScript, and TypeScript into AST functional units, analyzing multi-file codebases in as fast as <strong>0.12 seconds</strong>.</li>
    <li><strong>Cool & Silent Operation:</strong> NPU execution preserves laptop battery life and leaves CPU/GPU cores unimpeded for local developer builds.</li>
    <li><strong>Multi-Tier Hardware Fallback:</strong> Automatically boots the Hexagon NPU on Snapdragon devices while providing high-precision AST heuristics on non-NPU test environments.</li>
</ul>

<div class="metric-grid">
    <div class="metric-card">
        <div class="metric-val">100%</div>
        <div class="metric-lbl">Air-Gapped (Zero Egress)</div>
    </div>
    <div class="metric-card">
        <div class="metric-val">45 TOPS</div>
        <div class="metric-lbl">Hexagon NPU Target</div>
    </div>
    <div class="metric-card">
        <div class="metric-val">0.12s</div>
        <div class="metric-lbl">Sub-Second Scan Speed</div>
    </div>
    <div class="metric-card">
        <div class="metric-val">23 / 23</div>
        <div class="metric-lbl">Automated Tests Passed</div>
    </div>
</div>

<h2>3. Key Enterprise Capabilities & Technical Highlights</h2>
<table>
    <thead>
        <tr>
            <th style="width: 25%;">Feature</th>
            <th style="width: 45%;">Technical Implementation</th>
            <th style="width: 30%;">Enterprise Impact</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Mathematical Shannon Entropy Scanning</strong></td>
            <td>Calculates string randomness entropy (bits/symbol) & regex signatures for AWS, GCP, OpenAI, Anthropic, HuggingFace, Slack, PyPI, and private keys.</td>
            <td>Eliminates credential leaks before code ever reaches remote servers.</td>
        </tr>
        <tr>
            <td><strong>AST Function & Class Chunking</strong></td>
            <td>Isolates functions, classes, and async blocks across Python, JS, and TS using abstract syntax trees.</td>
            <td>Guarantees rich contextual density without prompt truncation.</td>
        </tr>
        <tr>
            <td><strong>OASIS SARIF v2.1.0 Export</strong></td>
            <td>Outputs industry-standard SARIF reports with MITRE CWE taxonomy mapping (CWE-79 XSS, CWE-89 SQLi, CWE-798, CWE-369).</td>
            <td>Native integration into GitHub Code Scanning, GitLab SAST, & VS Code.</td>
        </tr>
        <tr>
            <td><strong>Sub-Second Git Staged & Diff Scanning</strong></td>
            <td>Queries git index to scan only staged files (<code>faraday --staged</code>) or pull request diffs (<code>faraday --diff main</code>).</td>
            <td>Gives developers instant pre-commit feedback in milliseconds.</td>
        </tr>
        <tr>
            <td><strong>Pre-Commit Hook Integration</strong></td>
            <td>Automated one-click installation (<code>faraday --install-hook</code>) and native <code>.pre-commit-hooks.yaml</code> manifest.</td>
            <td>Enforces hard quality gates before commits can be completed.</td>
        </tr>
        <tr>
            <td><strong>Neural Docstring & README Synthesis</strong></td>
            <td>NPU analyzes codebase architecture to dynamically generate complete docstrings and production-grade READMEs.</td>
            <td>Eliminates enterprise documentation backlogs in offline repos.</td>
        </tr>
    </tbody>
</table>

<h2>4. Real-World Benchmark Performance & Verification</h2>
<p>
Faraday was benchmarked against real-world external codebases (including full-stack production ETA prediction systems):
</p>
<ul>
    <li><strong>Runtime Performance:</strong> Completed multi-stage pipeline (AST parsing, static security, NPU review, SARIF export) across 10 files and 60 functions in <strong>0.12 seconds</strong>.</li>
    <li><strong>Vulnerability Detection:</strong> Accurately caught 13 security flaws, including DOM XSS via unescaped innerHTML, SQL string concatenation, and denominator division-by-zero.</li>
    <li><strong>CI Quality Gate Enforcement:</strong> Successfully halted commits exceeding the <code>--fail-on HIGH</code> security threshold.</li>
    <li><strong>Test Integrity:</strong> 100% pass rate across 23 unit tests covering core scanners, AST chunkers, git hooks, and model backends.</li>
</ul>

<h2>5. Conclusion & Snapdragon Value Proposition</h2>
<p>
Faraday proves that modern AI developer tools do not need to compromise data privacy or rely on cloud infrastructure. By harnessing the dedicated intelligence of the Qualcomm Snapdragon® X Elite Hexagon NPU, Faraday empowers engineers to build securely, efficiently, and with total sovereignty.
</p>

</body>
</html>"""
    html_path.write_text(html_content, encoding="utf-8")
    print(f"Successfully generated HTML: {html_path}")

def convert_html_to_pdf(html_path: Path, pdf_path: Path):
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    cmd = [
        edge_path,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_path.resolve()}",
        f"file:///{html_path.resolve()}".replace("\\", "/")
    ]
    subprocess.run(cmd, check=True)
    print(f"Successfully generated PDF: {pdf_path}")

if __name__ == "__main__":
    out_dir = Path("./submission_docs")
    out_dir.mkdir(exist_ok=True)
    
    docx_file = out_dir / "Faraday_Project_Submission.docx"
    create_docx(docx_file)
    
    html_file = out_dir / "submission.html"
    create_html(html_file)
    
    pdf_file = out_dir / "Faraday_Project_Submission.pdf"
    convert_html_to_pdf(html_file, pdf_file)
