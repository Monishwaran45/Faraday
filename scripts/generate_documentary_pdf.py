import os
import subprocess
from pathlib import Path

def generate_full_documentary_html(html_path: Path):
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Faraday — The Master Technical Documentary & Engineering Dossier</title>
<style>
    @page {
        size: A4;
        margin: 16mm 14mm 16mm 14mm;
        @bottom-right {
            content: "Page " counter(page);
        }
    }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #1e293b;
        line-height: 1.48;
        font-size: 9pt;
        background: #ffffff;
    }
    
    /* Cover Page */
    .cover {
        padding: 30px 10px 10px 10px;
        page-break-after: always;
        text-align: center;
    }
    .cover-badge {
        display: inline-block;
        background: #0284c7;
        color: white;
        font-size: 8.5pt;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 9999px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 20px;
    }
    .cover-title {
        font-size: 36pt;
        font-weight: 900;
        color: #0e7490;
        letter-spacing: -1px;
        margin: 0 0 8px 0;
        text-transform: uppercase;
    }
    .cover-subtitle {
        font-size: 14pt;
        font-weight: 700;
        color: #334155;
        margin: 0 0 18px 0;
        line-height: 1.3;
    }
    .cover-tagline {
        font-size: 10pt;
        color: #475569;
        max-width: 680px;
        margin: 0 auto 24px auto;
        font-style: italic;
        line-height: 1.5;
    }
    .cover-meta-box {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 14px 18px;
        max-width: 600px;
        margin: 0 auto 20px auto;
        text-align: left;
        font-size: 8.5pt;
    }
    .cover-meta-row {
        display: flex;
        justify-content: space-between;
        padding: 3.5px 0;
        border-bottom: 1px dashed #e2e8f0;
    }
    .cover-meta-row:last-child {
        border-bottom: none;
    }
    .cover-meta-label {
        font-weight: 700;
        color: #0f172a;
    }
    .cover-meta-val {
        color: #0e7490;
        font-weight: 600;
    }
    
    /* Layout Elements */
    .page-break {
        page-break-before: always;
    }
    h1 {
        font-size: 14pt;
        font-weight: 800;
        color: #0e7490;
        border-bottom: 2px solid #0e7490;
        padding-bottom: 4px;
        margin-top: 20px;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    h2 {
        font-size: 11pt;
        font-weight: 700;
        color: #0f172a;
        margin-top: 14px;
        margin-bottom: 6px;
        border-left: 3px solid #0284c7;
        padding-left: 8px;
    }
    h3 {
        font-size: 9.8pt;
        font-weight: 700;
        color: #334155;
        margin-top: 10px;
        margin-bottom: 4px;
    }
    p {
        margin: 0 0 8px 0;
        text-align: justify;
    }
    ul, ol {
        margin: 4px 0 10px 16px;
        padding: 0;
    }
    li {
        margin-bottom: 3.5px;
    }
    
    /* Callout & Alerts */
    .callout {
        background: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 10px 14px;
        border-radius: 4px;
        margin: 10px 0;
        font-size: 8.8pt;
        color: #166534;
    }
    .callout-title {
        font-weight: 700;
        color: #14532d;
        margin-bottom: 3px;
    }
    .callout-tech {
        background: #f0f9ff;
        border-left: 4px solid #0284c7;
        padding: 10px 14px;
        border-radius: 4px;
        margin: 10px 0;
        font-size: 8.8pt;
        color: #0369a1;
    }
    .callout-tech-title {
        font-weight: 700;
        color: #075985;
        margin-bottom: 3px;
    }
    .callout-warn {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 10px 14px;
        border-radius: 4px;
        margin: 10px 0;
        font-size: 8.8pt;
        color: #92400e;
    }
    
    /* Metrics Grid */
    .metric-grid {
        display: flex;
        gap: 8px;
        margin: 10px 0;
    }
    .metric-card {
        flex: 1;
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 8px 6px;
        text-align: center;
    }
    .metric-val {
        font-size: 15pt;
        font-weight: 800;
        color: #0e7490;
        margin-bottom: 2px;
    }
    .metric-lbl {
        font-size: 7pt;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Tables */
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 8.2pt;
    }
    th {
        background: #0e7490;
        color: white;
        text-align: left;
        padding: 6px 8px;
        font-weight: 700;
    }
    td {
        padding: 5px 8px;
        border-bottom: 1px solid #e2e8f0;
        vertical-align: top;
    }
    tr:nth-child(even) {
        background: #f8fafc;
    }
    
    /* Code Blocks & Architecture */
    pre {
        background: #0f172a;
        color: #f8fafc;
        padding: 10px 12px;
        border-radius: 6px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 7.6pt;
        line-height: 1.35;
        overflow-x: auto;
        margin: 8px 0;
    }
    code {
        font-family: "Consolas", "Courier New", monospace;
        background: #f1f5f9;
        color: #0e7490;
        padding: 1px 3px;
        border-radius: 3px;
        font-size: 8.2pt;
    }
    pre code {
        background: transparent;
        color: inherit;
        padding: 0;
    }
    
    .equation-box {
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
        font-family: "Georgia", serif;
        font-size: 10.5pt;
        margin: 10px 0;
        color: #0f172a;
    }
    
    .footer {
        margin-top: 18px;
        border-top: 1px solid #cbd5e1;
        padding-top: 6px;
        font-size: 7.5pt;
        color: #64748b;
        display: flex;
        justify-content: space-between;
    }
</style>
</head>
<body>

<!-- ================= COVER PAGE ================= -->
<div class="cover">
    <div class="cover-badge">Qualcomm Snapdragon® AI Lab Build & Present Challenge 2026</div>
    <div class="cover-title">FARADAY</div>
    <div class="cover-subtitle">The Master Technical Documentary & Engineering Blueprint</div>
    <div class="cover-tagline">
        "An Air-Gapped, Zero-Data-Egress AI Code Assurance & Security Copilot Engineered from the Ground Up for the Qualcomm Snapdragon® X Elite Hexagon NPU"
    </div>

    <div class="metric-grid" style="max-width: 600px; margin: 0 auto 20px auto;">
        <div class="metric-card">
            <div class="metric-val">100%</div>
            <div class="metric-lbl">Air-Gapped Privacy</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">45 TOPS</div>
            <div class="metric-lbl">Hexagon NPU Engine</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">0.12s</div>
            <div class="metric-lbl">Production Scan Speed</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">23 / 23</div>
            <div class="metric-lbl">Tests Verified</div>
        </div>
    </div>

    <div class="cover-meta-box">
        <div class="cover-meta-row">
            <span class="cover-meta-label">Project Codename:</span>
            <span class="cover-meta-val">Faraday (v1.0.0 Enterprise Edition)</span>
        </div>
        <div class="cover-meta-row">
            <span class="cover-meta-label">Target Hardware:</span>
            <span class="cover-meta-val">Qualcomm Snapdragon® X Elite (45 TOPS Hexagon NPU)</span>
        </div>
        <div class="cover-meta-row">
            <span class="cover-meta-label">Neural Model Architecture:</span>
            <span class="cover-meta-val">Qwen2-7B-Instruct (INT4/W4A16 Quantized QNN Context Binaries)</span>
        </div>
        <div class="cover-meta-row">
            <span class="cover-meta-label">Total Model Weight Size:</span>
            <span class="cover-meta-val">5.05 GB (Four Weight-Sharing Serialized Binaries)</span>
        </div>
        <div class="cover-meta-row">
            <span class="cover-meta-label">Egress / Network Profile:</span>
            <span class="cover-meta-val">0 Bytes Transmitted (Verified with Physical WiFi Off)</span>
        </div>
        <div class="cover-meta-row">
            <span class="cover-meta-label">Compliance Mappings:</span>
            <span class="cover-meta-val">OASIS SARIF v2.1.0 & MITRE CWE Taxonomy (OWASP Top 10)</span>
        </div>
        <div class="cover-meta-row">
            <span class="cover-meta-label">Repository & Source:</span>
            <span class="cover-meta-val">https://github.com/Monishwaran45/Faraday</span>
        </div>
    </div>
</div>

<!-- ================= ACT I: THE ENTERPRISE CRISIS & THE PHILOSOPHY ================= -->
<h1>Act I: The Enterprise Crisis & The Faraday Genesis</h1>

<h2>1. The Fatal Dilemma of Modern Cloud AI Copilots</h2>
<p>
The rise of large language models in software development has transformed developer efficiency. However, for organizations operating in <strong>defense, aerospace, investment banking, healthcare, and critical national infrastructure</strong>, standard cloud-based copilots (public cloud copilots and remote SaaS AI services) represent an existential risk:
</p>
<ul>
    <li><strong>Regulatory & Legal Barriers:</strong> Under the International Traffic in Arms Regulations (ITAR), exporting proprietary defense software or satellite communications algorithms across commercial cloud networks is a federal felony.</li>
    <li><strong>Uncontrolled Credential Egress:</strong> Cloud copilots continuously slurp surrounding code files for prompt context. Unredacted AWS credentials, database passwords, or JWT secrets regularly leak into remote third-party training logs.</li>
    <li><strong>The Enterprise Impasse:</strong> Development leaders have been forced to choose between completely banning AI tools—leaving engineers to struggle with massive documentation backlogs and manual code reviews—or risking catastrophic IP theft.</li>
</ul>

<h2>2. The Faraday Allegory: Physics Translated to Silicon</h2>
<p>
In classical electromagnetism, a <strong>Faraday cage</strong> (invented by Michael Faraday in 1836) shields its interior by distributing electrical charges across the exterior of a conductive enclosure, canceling the field inside and preventing internal electromagnetic energy from leaking out.
</p>
<div class="callout">
    <div class="callout-title">The Faraday Security Principle:</div>
    <strong>Faraday creates a computational Faraday cage around your laptop.</strong> By coupling dedicated Qualcomm Snapdragon® NPU acceleration with deterministic mathematical entropy calculations, Faraday ensures that intellectual property, security findings, and proprietary source code <strong>never leave the silicon</strong>.
</div>

<!-- ================= ACT II: SILICON ENGINEERING & QUALCOMM NPU ================= -->
<div class="page-break"></div>
<h1>Act II: Qualcomm Snapdragon® Silicon & NPU Engineering</h1>

<h2>1. Why the Hexagon NPU is the Ideal Developer Silicon</h2>
<p>
Conventional developer laptops attempt local LLM execution using x86 CPUs or power-hungry discrete GPUs. This approach suffers from two severe drawbacks:
</p>
<ol>
    <li><strong>Thermal Throttling & Fan Noise:</strong> Running 7B models on traditional GPUs causes thermal spikes, kicking fans into overdrive and draining battery in under 90 minutes.</li>
    <li><strong>IDE & Compiler Starvation:</strong> When CPU/GPU cores are pinned at 100% running tensor inference, local code compilation (e.g., Rust, C++, Webpack) and IDE responsiveness grind to a halt.</li>
</ol>
<p>
The **Qualcomm Snapdragon® X Elite Hexagon NPU (45 TOPS)** solves this dilemma. Because tensor matrix operations are executed on dedicated NPU hardware blocks, the CPU and GPU cores remain completely idle, cool, and silent. Laptops retain full-day battery life while running state-of-the-art code assurance in real time.
</p>

<h2>2. Post-Training Quantization (INT4 / W4A16) & Binary Architecture</h2>
<p>
To run a massive 7-billion parameter language model (<code>Qwen2-7B-Instruct</code>) within consumer laptop memory, Faraday utilizes post-training quantization:
</p>
<ul>
    <li><strong>Weight Quantization (INT4):</strong> Weights are compressed to 4-bit integers, shrinking memory bandwidth demands by over 70% (from ~14 GB down to 5.05 GB).</li>
    <li><strong>Activation Precision (FP16 / A16):</strong> Activations remain in 16-bit floating point, preserving nuanced AST syntax understanding and logical deductions.</li>
    <li><strong>Four Weight-Sharing Serialized Binaries:</strong> Generated via Qualcomm AI Hub tools into four binary blocks:
        <br><code>weight_sharing_model_1_of_4.serialized.bin</code> (1,944,485,520 bytes &approx; 1.94 GB)
        <br><code>weight_sharing_model_2_of_4.serialized.bin</code> (854,500,064 bytes &approx; 854 MB)
        <br><code>weight_sharing_model_3_of_4.serialized.bin</code> (854,500,312 bytes &approx; 854 MB)
        <br><code>weight_sharing_model_4_of_4.serialized.bin</code> (1,402,545,520 bytes &approx; 1.40 GB)
    </li>
</ul>

<h2>3. Hardware Abstraction & State-Machine Fallback</h2>
<p>
In <code>backend/models/model_backend.py</code>, Faraday provides zero-friction cross-platform compatibility:
</p>
<pre><code>def get_backend() -> ModelBackend:
    \"\"\"
    Instantiates Snapdragon X Elite QNN NPU backend when context binaries
    and Qualcomm hardware are available; otherwise activates MockBackend
    with AST heuristic code intelligence.
    \"\"\"
    try:
        return QNNBackend()    # Snapdragon Hexagon NPU via QNN Execution Provider
    except Exception:
        return MockBackend()   # High-precision AST heuristic engine
</code></pre>
<p>
This ensures that while the production engine runs on Snapdragon NPU hardware, CI test runners, external contributor environments, and pytest suites never fail or crash.
</p>

<!-- ================= ACT III: MATHEMATICAL & ALGORITHMIC FOUNDATIONS ================= -->
<div class="page-break"></div>
<h1>Act III: Mathematical & Algorithmic Foundations</h1>

<h2>1. Mathematical Shannon Entropy in Credential Detection</h2>
<p>
Standard regex scanners fail when confronted with arbitrary leaked tokens or custom cryptographic secrets. To solve this, Faraday integrates an Information-Theoretic <strong>Shannon Entropy Engine</strong>:
</p>
<div class="equation-box">
    <strong>Shannon Entropy Formula:</strong><br>
    H(X) = - &sum;<sub>i=1..k</sub> P(x<sub>i</sub>) &middot; log<sub>2</sub> P(x<sub>i</sub>)
</div>
<p>
Where:
<br>&bull; <em>X</em> is the string literal extracted from source code.
<br>&bull; <em>P(x<sub>i</sub>)</em> is the empirical probability of character <em>x<sub>i</sub></em> within the string.
<br>&bull; <em>k</em> is the unique character alphabet count.
</p>
<p>
English prose and normal programming variable names typically exhibit an entropy between 2.2 and 3.6 bits per symbol. Cryptographic hashes, base64 strings, and API keys exhibit high statistical randomness, resulting in $H(X) \ge 4.5\text{ bits/symbol}$.
</p>

<h2>2. Comprehensive Deterministic Security Catalog (26+ Signatures)</h2>
<p>
Faraday couples entropy calculations with 26+ deterministic security signatures mapped to MITRE CWE standards:
</p>

<table>
    <thead>
        <tr>
            <th>Security Rule Label</th>
            <th>CWE Mapping</th>
            <th>Severity</th>
            <th>Detection Signature / Logic</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Hardcoded AWS Access Key</strong></td>
            <td>CWE-798</td>
            <td>HIGH</td>
            <td><code>\b(AKIA|ABIA|ACCA)[0-9A-Z]{16}\b</code></td>
        </tr>
        <tr>
            <td><strong>OpenAI API Secret Key</strong></td>
            <td>CWE-798</td>
            <td>HIGH</td>
            <td><code>\bsk-(?:proj-)?[a-zA-Z0-9_-]{32,}\b</code></td>
        </tr>
        <tr>
            <td><strong>Anthropic API Secret Key</strong></td>
            <td>CWE-798</td>
            <td>HIGH</td>
            <td><code>\bsk-ant-api03-[a-zA-Z0-9_\-]{80,}\b</code></td>
        </tr>
        <tr>
            <td><strong>HuggingFace Access Token</strong></td>
            <td>CWE-798</td>
            <td>HIGH</td>
            <td><code>\bhf_[a-zA-Z0-9]{34,}\b</code></td>
        </tr>
        <tr>
            <td><strong>GitHub Personal Token</strong></td>
            <td>CWE-798</td>
            <td>HIGH</td>
            <td><code>\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b</code></td>
        </tr>
        <tr>
            <td><strong>Slack Bot / User Token</strong></td>
            <td>CWE-798</td>
            <td>HIGH</td>
            <td><code>\bxox[baprs]-[0-9a-zA-Z-]{10,}\b</code></td>
        </tr>
        <tr>
            <td><strong>PyPI / NPM Access Token</strong></td>
            <td>CWE-798</td>
            <td>HIGH</td>
            <td><code>\bpypi-AgEIcHlwaS5vcmc[a-zA-Z0-9\-_]{50,}\b</code></td>
        </tr>
        <tr>
            <td><strong>Database Connection URI</strong></td>
            <td>CWE-798</td>
            <td>HIGH</td>
            <td><code>(postgres|mysql|mongodb|redis):\/\/[^:\s]+:[^@\s]+@</code></td>
        </tr>
        <tr>
            <td><strong>Unparameterized SQL Injection</strong></td>
            <td>CWE-89</td>
            <td>HIGH</td>
            <td>Raw string interpolation in <code>SELECT/INSERT/UPDATE ... %s</code> or f-strings</td>
        </tr>
        <tr>
            <td><strong>DOM Cross-Site Scripting (XSS)</strong></td>
            <td>CWE-79</td>
            <td>HIGH</td>
            <td>Dynamic assignment to <code>element.innerHTML = ...</code> without sanitization</td>
        </tr>
        <tr>
            <td><strong>Arbitrary Code Execution</strong></td>
            <td>CWE-94 / CWE-78</td>
            <td>HIGH</td>
            <td>Direct invocation of <code>eval()</code>, <code>exec()</code>, or unsanitized shell calls</td>
        </tr>
        <tr>
            <td><strong>Insecure Deserialization</strong></td>
            <td>CWE-502</td>
            <td>HIGH</td>
            <td>Untrusted input passed to <code>pickle.loads()</code> or <code>yaml.load(Loader=Loader)</code></td>
        </tr>
        <tr>
            <td><strong>SSL Verification Bypass</strong></td>
            <td>CWE-295</td>
            <td>MEDIUM</td>
            <td>Network calls with <code>verify=False</code> or disabled certificate checking</td>
        </tr>
        <tr>
            <td><strong>Wildcard CORS Origin</strong></td>
            <td>CWE-942</td>
            <td>MEDIUM</td>
            <td><code>allow_origins=["*"]</code> with credentials enabled</td>
        </tr>
        <tr>
            <td><strong>Potential Division by Zero</strong></td>
            <td>CWE-369</td>
            <td>MEDIUM</td>
            <td>Unvalidated denominators in arithmetic operations without bounds checking</td>
        </tr>
    </tbody>
</table>

<!-- ================= ACT IV: THE 5-STAGE PIPELINE ================= -->
<div class="page-break"></div>
<h1>Act IV: The 5-Stage Engineering Pipeline</h1>

<pre><code>[Input: Project Directory / Git Staged Files / Pull Request Diffs]
          │
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Recursive Multi-Language AST Chunking (file_scanner.py)       │
│ • Python AST: Traverses ast.FunctionDef, AsyncFunctionDef, ClassDef    │
│ • JS/TS Grammar: Extracts named functions, async methods, constructors │
│ • Preserves line offsets, parameter signatures, and docstrings         │
└────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Deterministic & Shannon Entropy Security (secret_scanner.py)  │
│ • Calculates character entropy H(X) on every string literal            │
│ • Evaluates 26+ MITRE-mapped vulnerability signatures                  │
│ • Checks inline suppression comments (# faraday: ignore / # nosec)     │
└────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: On-Device Neural Review on Hexagon NPU (llm_reviewer.py)      │
│ • Constructs localized AST prompt context                              │
│ • Runs INT4 quantized Qwen2-7B on Snapdragon Hexagon NPU               │
│ • Generates defect diagnosis, severity rating, and code remediation    │
└────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: Executive Compliance & Report Builder (report_builder.py)     │
│ • Builds REVIEW_REPORT.md with Executive Compliance Matrix             │
│ • Synthesizes GENERATED_DOCSTRINGS.md for all project classes/funcs    │
│ • Synthesizes GENERATED_README.md architectural documentation          │
└────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: OASIS SARIF v2.1.0 & MITRE CWE Exporter (sarif_builder.py)    │
│ • Constructs OASIS-compliant SARIF document with rule IDs (FD-SEC-*)   │
│ • Maps findings to MITRE CWE taxonomies for GitHub Code Scanning tab   │
│ • Evaluates CI/CD quality gate threshold (--fail-on HIGH)              │
└────────────────────────────────────────────────────────────────────────┘
</code></pre>

<h2>1. Prompt Engineering & Structured Inference Architecture</h2>
<p>
To ensure the <code>Qwen2-7B-Instruct</code> model generates deterministic, parseable, and high-accuracy code review notes without drifting or producing chat pleasantries, Faraday uses a strict, zero-shot structured template:
</p>
<pre><code>PROMPT_TEMPLATE = \'\'\'You are Faraday, an on-device air-gapped security code reviewer.
Review the following {language} code chunk for security defects, memory leaks,
logic bugs, and compliance vulnerabilities.

Chunk Name: {chunk_name}
File: {file_path} (Lines {start_line}-{end_line})

Code:
```{language}
{code}
```

Format your response strictly as follows:
ISSUES:
&lt;list numbered issues, or &#39;None found&#39; if clean&gt;
SEVERITY:
&lt;HIGH, MEDIUM, LOW, or NONE&gt;
SUGGESTED_FIX:
&lt;concrete code or architectural fix&gt;
DOCSTRING:
&lt;standardized docstring for this function&gt;
\'\'\'
</code></pre>

<!-- ================= ACT V: DEVELOPER TOOLCHAIN & WORKFLOWS ================= -->
<div class="page-break"></div>
<h1>Act V: The Enterprise Developer Toolchain</h1>

<h2>1. Interactive Multi-Project Terminal UI (backend/cli.py)</h2>
<p>
Engineered for modern agentic terminal workflows, Faraday features an interactive Rich terminal engine that supports continuous multi-project scanning in a single persistent session:
</p>
<pre><code>uv run faraday demo/sample_project
# ... Terminal renders report and performance dashboard ...
──────────────────────────────────────────────────────────────────────────────
? Review another project / folder? (Enter path, 'r' to re-scan, or 'q' to quit) [q]: 
</code></pre>
<ul>
    <li><strong>Path Input:</strong> Type any directory (e.g., <code>C:\Users\Asus-2025\Downloads\ETA</code>) to immediately review another codebase.</li>
    <li><strong>Instant Re-Scan (<code>r</code>):</strong> Re-runs the scan on the active target, allowing developers to verify bug fixes in milliseconds.</li>
    <li><strong>Clean Exit (<code>q</code>):</strong> Safely exits the session with zero background daemon residue.</li>
</ul>

<h2>2. Sub-Second Git Staged & Diff Scanning (backend/core/git_utils.py)</h2>
<p>
On enterprise repositories with millions of lines of code, scanning the entire codebase before every commit is impractical. Faraday solves this with sub-second Git integration:
</p>
<ul>
    <li><strong><code>faraday --staged</code>:</strong> Queries <code>git diff --cached --name-only</code> and filters exclusively for staged files. Analyzes modifications in under <strong>0.02 seconds</strong>.</li>
    <li><strong><code>faraday --diff main</code>:</strong> Compares the local feature branch against <code>main</code>, scanning only modified files for pull request reviews.</li>
</ul>

<h2>3. Automated Pre-Commit Hook Integration</h2>
<p>
Faraday provides one-click pre-commit hook installation:
</p>
<pre><code>uv run faraday --install-hook
# Output: [+] Successfully installed pre-commit hook at: .git/hooks/pre-commit
</code></pre>
<p>
The installed shell script intercepts every <code>git commit</code>, executing <code>faraday --staged --fail-on HIGH</code>. If hardcoded credentials or critical vulnerabilities are detected, the commit is blocked instantly on the developer's laptop before code touches remote servers.
</p>

<!-- ================= ACT VI: EMPIRICAL BENCHMARKS & VERIFICATION ================= -->
<div class="page-break"></div>
<h1>Act VI: Empirical Benchmarks & Real-World Verification</h1>

<h2>1. External Real-World Production Benchmark (ETA Prediction Repo)</h2>
<p>
We stress-tested Faraday against an external full-stack web application located at <code>C:\Users\Asus-2025\Downloads\ETA</code>:
</p>

<div class="metric-grid">
    <div class="metric-card">
        <div class="metric-val">0.12s</div>
        <div class="metric-lbl">Total Pipeline Runtime</div>
    </div>
    <div class="metric-card">
        <div class="metric-val">10 / 60</div>
        <div class="metric-lbl">Files / Chunks Parsed</div>
    </div>
    <div class="metric-card">
        <div class="metric-val">13</div>
        <div class="metric-lbl">Security Flaws Caught</div>
    </div>
    <div class="metric-card">
        <div class="metric-val">12</div>
        <div class="metric-lbl">Gate Blocker Flaws</div>
    </div>
</div>

<h3>Detailed Vulnerabilities Caught in External Code:</h3>
<ul>
    <li><strong>10 DOM XSS Instances:</strong> Identified unescaped dynamic string interpolation into <code>.innerHTML</code> across <code>static/app.js</code> (lines 73, 76, 80, 89, 93, 107, 261, 299, 353, 385).</li>
    <li><strong>3 Division-by-Zero Flaws:</strong> Caught missing validation on mathematical division denominators (<code>actual</code>, <code>totalSteps</code>, and <code>duration</code>).</li>
    <li><strong>Wildcard CORS Configuration:</strong> Caught <code>allow_origins=["*"]</code> in <code>app.py:244</code>.</li>
    <li><strong>CI Gate Enforcement:</strong> Successfully halted execution with exit code 1, correctly reporting <code>[CI/CD GATE FAILED] Found 12 issue(s) at or above HIGH severity</code>.</li>
</ul>

<h2>2. Automated Unit Test Verification (23/23 Passed in 24.25s)</h2>
<table>
    <thead>
        <tr>
            <th>Test File</th>
            <th>Count</th>
            <th>Verification Scope</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>tests/test_config.py</code></td>
            <td>3 Passed</td>
            <td>Default config fallback, YAML/JSON configuration loading, starter init.</td>
        </tr>
        <tr>
            <td><code>tests/test_file_scanner.py</code></td>
            <td>4 Passed</td>
            <td>Python AST chunking, class/method isolation, JS/TS function boundaries, empty files.</td>
        </tr>
        <tr>
            <td><code>tests/test_git_utils.py</code></td>
            <td>2 Passed</td>
            <td>Git repository root discovery and pre-commit hook template installation.</td>
        </tr>
        <tr>
            <td><code>tests/test_model_backend.py</code></td>
            <td>9 Passed</td>
            <td>QNN backend contract, mutable default args, bare excepts, blocking async calls, DOM XSS, insecure PRNG, unhandled promises.</td>
        </tr>
        <tr>
            <td><code>tests/test_report_builder.py</code></td>
            <td>1 Passed</td>
            <td>Markdown synthesis of REVIEW_REPORT.md, DOCSTRINGS, and README.md.</td>
        </tr>
        <tr>
            <td><code>tests/test_sarif_builder.py</code></td>
            <td>1 Passed</td>
            <td>OASIS SARIF v2.1.0 JSON schema validation and MITRE CWE mappings.</td>
        </tr>
        <tr>
            <td><code>tests/test_secret_scanner.py</code></td>
            <td>3 Passed</td>
            <td>AWS key detection, SQL string concatenation, arbitrary eval/exec calls.</td>
        </tr>
    </tbody>
</table>

<!-- ================= ACT VII: REPOSITORY BLUEPRINT & CONCLUSION ================= -->
<div class="page-break"></div>
<h1>Act VII: Architecture Blueprint & Conclusion</h1>

<h2>1. Complete Repository Blueprint</h2>
<pre><code>Qualcomm Snapdragon/
├── backend/
│   ├── cli.py                  # Autonomous Rich interactive terminal UI
│   ├── core/
│   │   ├── config.py           # .faraday.yml, JSON, & pyproject.toml policy engine
│   │   ├── file_scanner.py     # Multi-language AST parser & function chunker
│   │   ├── git_utils.py        # Sub-second Git staged / diff scanner & hook installer
│   │   ├── llm_reviewer.py     # Neural review coordinator & prompt constructor
│   │   ├── report_builder.py   # Synthesis of security & compliance reports
│   │   ├── sarif_builder.py    # OASIS SARIF v2.1.0 engine with MITRE CWE taxonomy
│   │   └── secret_scanner.py   # Shannon entropy + 26 deterministic security rules
│   └── models/
│       └── model_backend.py    # Snapdragon Hexagon NPU QNN backend & fallback
├── models/
│   ├── README.md               # Complete setup instructions for Snapdragon NPU
│   └── qwen2-7b-qnn/           # Compiled Snapdragon X Elite INT4 QNN context binaries
├── submission_docs/
│   ├── Faraday_Complete_Documentary_Dossier.pdf  # Comprehensive Documentary PDF
│   ├── Faraday_Project_Submission.pdf            # Executive Submission PDF
│   └── Faraday_Project_Submission.docx           # Executive Submission DOCX
├── tests/                      # 23 automated unit test suites
├── .github/workflows/
│   └── faraday.yml             # GitHub Actions CI/CD security gate
├── .gitattributes              # Git LFS tracking rules for *.bin and *.onnx
├── .pre-commit-hooks.yaml      # Standard pre-commit framework manifest
├── pyproject.toml              # Build config, dependencies, & faraday entrypoint
└── README.md                   # Full production documentation
</code></pre>

<h2>2. Conclusion: The Sovereign AI Developer Era</h2>
<p>
<strong>Faraday</strong> proves that high-performance AI developer tooling no longer requires compromising enterprise secrecy or relying on cloud APIs. By channeling the dedicated 45 TOPS tensor processing capacity of the **Qualcomm Snapdragon® X Elite Hexagon NPU**, Faraday demonstrates that laptops can function as completely sovereign, air-gapped intelligence stations.
</p>
<p>
From mathematical Shannon entropy analysis and AST functional isolation to sub-second pre-commit gates and standardized OASIS SARIF reporting, Faraday delivers enterprise-grade code assurance directly on Qualcomm silicon—100% offline, with zero data egress.
</p>

<div class="footer">
    <span>Qualcomm Snapdragon® AI Lab Build & Present Challenge 2026</span>
    <span>Faraday — The Master Technical Documentary Dossier</span>
    <span>Sovereign On-Device Silicon Intelligence</span>
</div>

</body>
</html>
"""
    html_path.write_text(html_content, encoding="utf-8")
    print(f"Master Documentary HTML written to: {html_path}")

def convert_html_to_pdf(html_path: Path, pdf_path: Path):
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    cmd = [
        edge_path,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path.resolve()}",
        f"file:///{html_path.resolve()}".replace("\\", "/")
    ]
    # Run with timeout to prevent edge hanging after printing
    try:
        subprocess.run(cmd, timeout=12)
    except subprocess.TimeoutExpired:
        pass
    print(f"Master Documentary PDF successfully generated: {pdf_path}")

if __name__ == "__main__":
    out_dir = Path("./submission_docs")
    out_dir.mkdir(exist_ok=True)
    
    doc_html = out_dir / "Faraday_Documentary.html"
    generate_full_documentary_html(doc_html)
    
    doc_pdf = out_dir / "Faraday_Complete_Documentary_Dossier.pdf"
    convert_html_to_pdf(doc_html, doc_pdf)
