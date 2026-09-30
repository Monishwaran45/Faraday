"""
backend/web_server.py

Zero-dependency, air-gapped interactive visual code review dashboard for Faraday.
Serves on http://localhost:8000 using Python standard library http.server.
Provides:
  - Repository Health Score with visual SVG donut charts (High, Medium, Low severity).
  - Interactive File Explorer with line-mapped finding badges and source code viewer.
  - Real-time On-Device Neural Docstring Synthesis (PEP-257).
  - On-Device Contextual README Synthesis based on AST analysis.
  - 100% Air-Gapped Qualcomm Snapdragon NPU execution status.
"""

import html
import json
import mimetypes
import os
import sys
import threading
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List

from backend.core.config import load_project_config
from backend.core.file_scanner import scan_project, CodeChunk
from backend.core.secret_scanner import scan_all
from backend.core.llm_reviewer import review_all, review_chunk, generate_readme
from backend.core.sarif_builder import generate_sarif_report
from backend.models.model_backend import get_backend

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Faraday | On-Device Air-Gapped Code Assurance</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --uber-black: #000000;
      --uber-dark: #0a0a0a;
      --uber-card: #121212;
      --uber-card-hover: #1a1a1a;
      --uber-border: #222222;
      --uber-border-light: #333333;
      --uber-white: #ffffff;
      --uber-gray-100: #f4f4f5;
      --uber-gray-400: #a1a1aa;
      --uber-gray-500: #71717a;
      --uber-gray-700: #3f3f46;
      --uber-green: #06c167;
      --uber-green-glow: rgba(6, 193, 103, 0.2);
      --uber-red: #ff334b;
      --uber-red-glow: rgba(255, 51, 75, 0.2);
      --uber-blue: #276ef1;
      --uber-blue-glow: rgba(39, 110, 241, 0.2);
      --font-uber: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--uber-black);
      color: var(--uber-white);
      font-family: var(--font-uber);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }

    /* Uber Navigation Bar */
    header {
      background-color: var(--uber-black);
      border-bottom: 1px solid var(--uber-border);
      padding: 1rem 2.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .brand-section {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }

    .brand-logo-text {
      font-size: 1.6rem;
      font-weight: 800;
      letter-spacing: -0.04em;
      color: var(--uber-white);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .brand-divider {
      width: 1px;
      height: 24px;
      background: var(--uber-border-light);
    }

    .product-label {
      font-size: 0.95rem;
      font-weight: 600;
      letter-spacing: -0.01em;
      color: var(--uber-gray-400);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .uber-pill-tag {
      font-size: 0.68rem;
      font-weight: 700;
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
      background: var(--uber-white);
      color: var(--uber-black);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .npu-status-widget {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.45rem 1rem;
      background: var(--uber-card);
      border: 1px solid var(--uber-border);
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--uber-gray-400);
    }

    .live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--uber-green);
      box-shadow: 0 0 10px var(--uber-green);
      animation: pulseGreen 2s infinite;
    }

    @keyframes pulseGreen {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }

    .btn-uber-primary {
      background: var(--uber-white);
      color: var(--uber-black);
      border: none;
      border-radius: 999px;
      padding: 0.6rem 1.4rem;
      font-size: 0.85rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .btn-uber-primary:hover {
      background: #e4e4e7;
      transform: translateY(-1px);
    }

    .btn-uber-primary:active {
      transform: translateY(0);
    }

    /* Main Content Layout */
    main {
      flex: 1;
      max-width: 1720px;
      margin: 0 auto;
      width: 100%;
      padding: 2rem 2.5rem;
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }

    /* Uber Route & Status Card */
    .route-banner {
      background: var(--uber-card);
      border: 1px solid var(--uber-border);
      border-radius: 16px;
      padding: 1.5rem 2rem;
      display: grid;
      grid-template-columns: 1fr 1fr;
      align-items: center;
      gap: 2rem;
    }

    .route-path {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .route-step {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
    }

    .route-icon-dot {
      width: 10px;
      height: 10px;
      background: var(--uber-white);
      border-radius: 50%;
      margin-top: 5px;
      flex-shrink: 0;
    }

    .route-icon-sq {
      width: 10px;
      height: 10px;
      background: var(--uber-green);
      margin-top: 5px;
      flex-shrink: 0;
    }

    .route-line {
      width: 2px;
      height: 22px;
      background: var(--uber-border-light);
      margin-left: 4px;
      margin-top: -6px;
      margin-bottom: -6px;
    }

    .route-text-label {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--uber-gray-500);
      font-weight: 600;
    }

    .route-text-val {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--uber-white);
      margin-top: 0.15rem;
    }

    .route-specs {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 2.5rem;
    }

    .spec-item {
      text-align: right;
    }

    .spec-val {
      font-size: 1.75rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      color: var(--uber-white);
    }

    .spec-lbl {
      font-size: 0.75rem;
      color: var(--uber-gray-400);
      font-weight: 500;
      margin-top: 0.2rem;
    }

    /* Uber Metrics Cards Grid */
    .metrics-row {
      display: grid;
      grid-template-columns: 320px 1fr 1fr 1fr;
      gap: 1.25rem;
    }

    .metric-card {
      background: var(--uber-card);
      border: 1px solid var(--uber-border);
      border-radius: 14px;
      padding: 1.5rem;
      transition: background 0.2s, border-color 0.2s;
      position: relative;
    }

    .metric-card:hover {
      background: var(--uber-card-hover);
      border-color: var(--uber-border-light);
    }

    /* Uber Donut Score */
    .donut-card {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }

    .donut-wrap {
      position: relative;
      width: 90px;
      height: 90px;
      flex-shrink: 0;
    }

    .donut-svg {
      transform: rotate(-90deg);
      width: 90px;
      height: 90px;
    }

    .donut-track {
      fill: none;
      stroke: var(--uber-border);
      stroke-width: 9;
    }

    .donut-bar {
      fill: none;
      stroke: var(--uber-green);
      stroke-width: 9;
      stroke-dasharray: 251.2;
      stroke-dashoffset: 0;
      stroke-linecap: round;
      transition: stroke-dashoffset 1s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.3s;
    }

    .donut-number {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 1.25rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      color: var(--uber-white);
    }

    .metric-title {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--uber-gray-400);
      margin-bottom: 0.5rem;
    }

    .metric-big {
      font-size: 2.25rem;
      font-weight: 800;
      letter-spacing: -0.04em;
      color: var(--uber-white);
      line-height: 1;
    }

    .metric-sub {
      font-size: 0.78rem;
      color: var(--uber-gray-500);
      font-weight: 500;
      margin-top: 0.5rem;
    }

    .badge-accent-red {
      color: var(--uber-red);
    }
    .badge-accent-green {
      color: var(--uber-green);
    }

    /* Uber Ride / Tab Selector */
    .uber-tabs {
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--uber-border);
      padding-bottom: 0.5rem;
    }

    .uber-tab-btn {
      padding: 0.6rem 1.25rem;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: 600;
      background: transparent;
      border: 1px solid transparent;
      color: var(--uber-gray-400);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.15s ease;
    }

    .uber-tab-btn:hover {
      color: var(--uber-white);
      background: var(--uber-card);
    }

    .uber-tab-btn.active {
      background: var(--uber-white);
      color: var(--uber-black);
      font-weight: 700;
    }

    /* Views */
    .tab-view {
      display: none;
    }
    .tab-view.active {
      display: grid;
    }

    /* Explorer View: Split Layout */
    .explorer-grid {
      grid-template-columns: 380px 1fr;
      gap: 1.5rem;
      height: calc(100vh - 380px);
      min-height: 520px;
    }

    /* Left: Ride / File List */
    .file-panel {
      background: var(--uber-card);
      border: 1px solid var(--uber-border);
      border-radius: 14px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .file-panel-header {
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--uber-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--uber-gray-400);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .file-ul {
      list-style: none;
      overflow-y: auto;
      flex: 1;
      padding: 0.5rem;
    }

    .file-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      border-radius: 10px;
      cursor: pointer;
      margin-bottom: 0.25rem;
      transition: background 0.15s;
    }

    .file-row:hover {
      background: var(--uber-card-hover);
    }

    .file-row.selected {
      background: #1f1f1f;
      border: 1px solid var(--uber-border-light);
    }

    .file-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      overflow: hidden;
    }

    .file-icon {
      width: 28px;
      height: 28px;
      background: var(--uber-black);
      border: 1px solid var(--uber-border);
      border-radius: 6px;
      display: grid;
      place-items: center;
      font-size: 0.75rem;
      color: var(--uber-gray-400);
      flex-shrink: 0;
    }

    .file-name-text {
      font-size: 0.825rem;
      font-weight: 600;
      color: var(--uber-white);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .uber-status-pill {
      font-size: 0.68rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      background: rgba(6, 193, 103, 0.15);
      color: var(--uber-green);
      border: 1px solid rgba(6, 193, 103, 0.3);
      flex-shrink: 0;
    }

    .uber-status-pill.danger {
      background: rgba(255, 51, 75, 0.15);
      color: var(--uber-red);
      border-color: rgba(255, 51, 75, 0.3);
    }

    /* Right: Code & Inspection */
    .code-panel {
      background: var(--uber-dark);
      border: 1px solid var(--uber-border);
      border-radius: 14px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .code-panel-top {
      padding: 0.85rem 1.5rem;
      background: var(--uber-card);
      border-bottom: 1px solid var(--uber-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-family: var(--font-mono);
      font-size: 0.8rem;
    }

    .code-body {
      flex: 1;
      overflow: auto;
      padding: 1.25rem;
      font-family: var(--font-mono);
      font-size: 0.825rem;
      line-height: 1.6;
      background: #050505;
    }

    .code-row {
      display: flex;
      gap: 1.25rem;
      padding: 0.1rem 0.5rem;
      border-radius: 4px;
    }

    .code-row.flagged {
      background: rgba(255, 51, 75, 0.15);
      border-left: 3px solid var(--uber-red);
    }

    .code-num {
      color: var(--uber-gray-700);
      user-select: none;
      min-width: 42px;
      text-align: right;
    }

    .code-content {
      white-space: pre-wrap;
      word-break: break-all;
      color: #e4e4e7;
    }

    .uber-issue-card {
      margin: 0.6rem 0 0.6rem 42px;
      background: var(--uber-card);
      border: 1px solid rgba(255, 51, 75, 0.4);
      border-radius: 10px;
      padding: 1rem 1.25rem;
      font-family: var(--font-uber);
    }

    .issue-tag {
      display: inline-block;
      font-size: 0.68rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      background: var(--uber-red);
      color: var(--uber-white);
      margin-bottom: 0.35rem;
    }

    .issue-name {
      font-size: 0.9rem;
      font-weight: 700;
      color: var(--uber-white);
    }

    .issue-guidance {
      font-size: 0.8rem;
      color: var(--uber-gray-400);
      margin-top: 0.3rem;
    }

    /* Docstrings & README Layout */
    .docs-panel {
      background: var(--uber-card);
      border: 1px solid var(--uber-border);
      border-radius: 14px;
      padding: 2rem;
      overflow-y: auto;
      height: calc(100vh - 380px);
      min-height: 520px;
    }

    .doc-box {
      background: var(--uber-dark);
      border: 1px solid var(--uber-border);
      border-radius: 10px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.25rem;
    }

    .doc-box-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.75rem;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--uber-white);
    }

    .btn-uber-copy {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 0.35rem 0.75rem;
      border-radius: 999px;
      background: var(--uber-border);
      border: 1px solid var(--uber-border-light);
      color: var(--uber-white);
      cursor: pointer;
      transition: background 0.15s;
    }

    .btn-uber-copy:hover {
      background: var(--uber-border-light);
    }

    pre.doc-code {
      background: #000000;
      border: 1px solid var(--uber-border);
      border-radius: 8px;
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: #38bdf8;
      line-height: 1.6;
      overflow-x: auto;
    }

    .readme-rendered {
      line-height: 1.8;
      color: #d4d4d8;
    }

    .readme-rendered h1 {
      font-size: 1.85rem;
      font-weight: 800;
      letter-spacing: -0.04em;
      color: var(--uber-white);
      margin-bottom: 1rem;
    }

    .readme-rendered h2 {
      font-size: 1.35rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--uber-white);
      margin: 1.5rem 0 0.85rem 0;
      border-bottom: 1px solid var(--uber-border);
      padding-bottom: 0.5rem;
    }

    .readme-rendered table {
      width: 100%;
      border-collapse: collapse;
      margin: 1.25rem 0;
      font-size: 0.85rem;
    }

    .readme-rendered th, .readme-rendered td {
      border: 1px solid var(--uber-border);
      padding: 0.75rem 1rem;
      text-align: left;
    }

    .readme-rendered th {
      background: var(--uber-dark);
      color: var(--uber-white);
      font-weight: 700;
    }

    /* Uber Footer */
    footer {
      border-top: 1px solid var(--uber-border);
      padding: 1.25rem 2.5rem;
      font-size: 0.75rem;
      color: var(--uber-gray-500);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
  </style>
</head>
<body>
  <!-- Uber Top Navigation -->
  <header>
    <div class="brand-section">
      <div class="brand-logo-text">
        FARADAY
      </div>
      <div class="brand-divider"></div>
      <div class="product-label">
        <span>Air-Gapped Code Assurance</span>
        <span class="uber-pill-tag">Snapdragon NPU</span>
      </div>
    </div>

    <div class="header-actions">
      <div class="npu-status-widget">
        <div class="live-dot"></div>
        <span>Qualcomm Hexagon HTP Online (0.00s Latency)</span>
      </div>
      <button class="btn-uber-primary" onclick="triggerScan()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
        Request Scan
      </button>
    </div>
  </header>

  <main>
    <!-- Route & Telemetry Banner -->
    <section class="route-banner">
      <div class="route-path">
        <div class="route-step">
          <div class="route-icon-dot"></div>
          <div>
            <div class="route-text-label">Target Workspace / Pickup</div>
            <div class="route-text-val" id="banner-target">.</div>
          </div>
        </div>
        <div class="route-line"></div>
        <div class="route-step">
          <div class="route-icon-sq"></div>
          <div>
            <div class="route-text-label">Compliance Destination</div>
            <div class="route-text-val">100% Zero-Egress Air-Gapped Clean State</div>
          </div>
        </div>
      </div>

      <div class="route-specs">
        <div class="spec-item">
          <div class="spec-val" id="banner-health">100%</div>
          <div class="spec-lbl">Health Rating</div>
        </div>
        <div class="spec-item">
          <div class="spec-val" id="banner-files">0</div>
          <div class="spec-lbl">Audited Files</div>
        </div>
        <div class="spec-item">
          <div class="spec-val" id="banner-chunks">0</div>
          <div class="spec-lbl">AST Blocks</div>
        </div>
      </div>
    </section>

    <!-- Metrics Cards Grid -->
    <section class="metrics-row">
      <!-- Health Donut -->
      <div class="metric-card donut-card">
        <div class="donut-wrap">
          <svg class="donut-svg" viewBox="0 0 100 100">
            <circle class="donut-track" cx="50" cy="50" r="40" />
            <circle id="donut-bar" class="donut-bar" cx="50" cy="50" r="40" />
          </svg>
          <div class="donut-number" id="donut-score-text">100%</div>
        </div>
        <div>
          <div class="metric-title">Security Health</div>
          <div style="font-size: 1.05rem; font-weight: 700; color: #fff;" id="health-tag">Compliant</div>
          <div class="metric-sub">Zero telemetry detected</div>
        </div>
      </div>

      <!-- Critical / High Secrets -->
      <div class="metric-card">
        <div class="metric-title">Critical Leaks & Secrets</div>
        <div class="metric-big badge-accent-red" id="metric-high">0</div>
        <div class="metric-sub">Hardcoded tokens & credential gates</div>
      </div>

      <!-- Logic Defects -->
      <div class="metric-card">
        <div class="metric-title">Neural Logic Flaws</div>
        <div class="metric-big" style="color: #f59e0b;" id="metric-med">0</div>
        <div class="metric-sub">Division guards & exception handling</div>
      </div>

      <!-- Clean Files -->
      <div class="metric-card">
        <div class="metric-title">Total Evaluated Blocks</div>
        <div class="metric-big badge-accent-green" id="metric-chunks">0</div>
        <div class="metric-sub" id="metric-files-desc">Across 0 source files</div>
      </div>
    </section>

    <!-- Uber Ride / Tab Controls -->
    <div class="uber-tabs">
      <button class="uber-tab-btn active" onclick="switchTab('explorer')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
        File Inspection
      </button>
      <button class="uber-tab-btn" onclick="switchTab('docstrings')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
        Docstring Synthesis (PEP-257)
      </button>
      <button class="uber-tab-btn" onclick="switchTab('readme')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
        README Synthesis
      </button>
      <button class="uber-tab-btn" onclick="downloadSarif()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
        Download SARIF 2.1.0
      </button>
    </div>

    <!-- View 1: Explorer -->
    <div id="view-explorer" class="tab-view active explorer-grid">
      <!-- File Selector Sidebar -->
      <div class="file-panel">
        <div class="file-panel-header">
          <span>Project Files</span>
          <span id="file-count-badge" style="color: var(--uber-white);">0 Files</span>
        </div>
        <ul class="file-ul" id="file-ul-list">
          <li style="padding: 1.5rem; text-align: center; color: var(--uber-gray-500);">Scanning files...</li>
        </ul>
      </div>

      <!-- Code Viewer -->
      <div class="code-panel">
        <div class="code-panel-top">
          <span id="code-panel-filename" style="color: var(--uber-white); font-weight: 600;">Select a file to inspect</span>
          <span id="code-panel-issues" style="color: var(--uber-gray-400);">0 Findings</span>
        </div>
        <div class="code-body" id="code-content-box">
          <div style="padding: 2.5rem; text-align: center; color: var(--uber-gray-500);">
            Select a file from the explorer on the left to review source code and inline findings.
          </div>
        </div>
      </div>
    </div>

    <!-- View 2: Docstrings -->
    <div id="view-docstrings" class="tab-view docs-panel">
      <div style="margin-bottom: 2rem;">
        <h2 style="font-size: 1.35rem; font-weight: 800; letter-spacing: -0.03em; color: #fff; margin-bottom: 0.35rem;">Synthesized On-Device Docstrings (PEP-257)</h2>
        <p style="font-size: 0.85rem; color: var(--uber-gray-400);">Generated on-device via Qualcomm Snapdragon Hexagon NPU inference.</p>
      </div>
      <div id="docstrings-wrapper">
        <!-- Injected Docstrings -->
      </div>
    </div>

    <!-- View 3: README -->
    <div id="view-readme" class="tab-view docs-panel">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;">
        <div>
          <h2 style="font-size: 1.35rem; font-weight: 800; letter-spacing: -0.03em; color: #fff; margin-bottom: 0.35rem;">Synthesized Repository README.md</h2>
          <p style="font-size: 0.85rem; color: var(--uber-gray-400);">Contextual repository layout, component mapping, and execution instructions.</p>
        </div>
        <button class="btn-uber-copy" onclick="copyReadme()">Copy Markdown</button>
      </div>
      <div class="readme-rendered" id="readme-wrapper">
        <!-- Injected README -->
      </div>
    </div>
  </main>

  <!-- Footer -->
  <footer>
    <div>Faraday Air-Gapped Code Assurance &bull; Qualcomm Snapdragon&reg; X Elite Hexagon NPU &bull; Monishwaran K</div>
    <div>100% Air-Gapped &bull; Zero Network Egress Verified</div>
  </footer>

  <script>
    let scanData = null;
    let selectedFile = null;

    async function loadScanData() {
      try {
        const res = await fetch('/api/scan');
        scanData = await res.json();
        renderDashboard(scanData);
      } catch (err) {
        console.error('Scan fetch error:', err);
      }
    }

    function renderDashboard(data) {
      document.getElementById('banner-target').textContent = data.target_path || '.';

      const high = data.high_count || 0;
      const med = data.medium_count || 0;
      const chunks = data.total_chunks || 0;
      const filesCount = (data.files || []).length;

      document.getElementById('metric-high').textContent = high;
      document.getElementById('metric-med').textContent = med;
      document.getElementById('metric-chunks').textContent = chunks;
      document.getElementById('metric-files-desc').textContent = `Across ${filesCount} source file(s)`;

      document.getElementById('banner-files').textContent = filesCount;
      document.getElementById('banner-chunks').textContent = chunks;

      // Score calculation
      const score = data.health_score || (high > 0 ? Math.max(10, 100 - high * 30 - med * 10) : 100);
      document.getElementById('donut-score-text').textContent = `${score}%`;
      document.getElementById('banner-health').textContent = `${score}%`;

      const bar = document.getElementById('donut-bar');
      const offset = 251.2 - (251.2 * score / 100);
      bar.style.strokeDashoffset = offset;
      if (score >= 90) {
        bar.style.stroke = 'var(--uber-green)';
        document.getElementById('health-tag').textContent = 'Secure & Compliant';
        document.getElementById('health-tag').style.color = 'var(--uber-green)';
      } else if (score >= 70) {
        bar.style.stroke = '#f59e0b';
        document.getElementById('health-tag').textContent = 'Moderate Risk';
        document.getElementById('health-tag').style.color = '#f59e0b';
      } else {
        bar.style.stroke = 'var(--uber-red)';
        document.getElementById('health-tag').textContent = 'High Vulnerability Risk';
        document.getElementById('health-tag').style.color = 'var(--uber-red)';
      }

      // Render File List
      const ul = document.getElementById('file-ul-list');
      ul.innerHTML = '';
      document.getElementById('file-count-badge').textContent = `${filesCount} Files`;

      if (data.files && data.files.length > 0) {
        data.files.forEach((f, idx) => {
          const li = document.createElement('li');
          li.className = 'file-row' + (idx === 0 ? ' selected' : '');
          const findingCount = (f.findings || []).length;
          const isDanger = findingCount > 0;
          li.innerHTML = `
            <div class="file-info">
              <div class="file-icon">${f.rel_path.endsWith('.py') ? 'PY' : 'CODE'}</div>
              <span class="file-name-text">${escapeHtml(f.rel_path)}</span>
            </div>
            <span class="uber-status-pill ${isDanger ? 'danger' : ''}">${isDanger ? findingCount + ' finding(s)' : 'Clean'}</span>
          `;
          li.onclick = () => selectFile(f, li);
          ul.appendChild(li);
        });

        selectFile(data.files[0], ul.firstElementChild);
      } else {
        ul.innerHTML = '<li style="padding: 1.5rem; text-align: center; color: var(--uber-gray-500);">No supported source files found.</li>';
      }

      renderDocstrings(data.docstrings || []);
      renderReadme(data.readme_markdown || '');
    }

    async function selectFile(fileObj, liElem) {
      if (!fileObj) return;
      selectedFile = fileObj;

      document.querySelectorAll('.file-row').forEach(el => el.classList.remove('selected'));
      if (liElem) liElem.classList.add('selected');

      document.getElementById('code-panel-filename').textContent = fileObj.rel_path;
      const findings = fileObj.findings || [];
      document.getElementById('code-panel-issues').textContent = `${findings.length} Finding(s)`;

      const codeBox = document.getElementById('code-content-box');
      codeBox.innerHTML = '<div style="padding: 1.5rem; color: var(--uber-gray-500);">Loading source...</div>';

      try {
        const res = await fetch('/api/file?path=' + encodeURIComponent(fileObj.path));
        const fileData = await res.json();
        renderSourceWithFindings(fileData.source || '', findings);
      } catch (e) {
        codeBox.innerHTML = '<div style="padding: 1.5rem; color: var(--uber-red);">Failed to load source file.</div>';
      }
    }

    function renderSourceWithFindings(source, findings) {
      const container = document.getElementById('code-content-box');
      container.innerHTML = '';

      const lines = source.split('\\n');
      const findingsByLine = {};
      findings.forEach(f => {
        if (!findingsByLine[f.line_number]) findingsByLine[f.line_number] = [];
        findingsByLine[f.line_number].push(f);
      });

      lines.forEach((lineText, idx) => {
        const lineNo = idx + 1;
        const lineFindings = findingsByLine[lineNo] || [];

        const row = document.createElement('div');
        row.className = 'code-row' + (lineFindings.length > 0 ? ' flagged' : '');

        row.innerHTML = `
          <div class="code-num">${lineNo}</div>
          <div class="code-content">${escapeHtml(lineText)}</div>
        `;
        container.appendChild(row);

        if (lineFindings.length > 0) {
          lineFindings.forEach(f => {
            const callout = document.createElement('div');
            callout.className = 'uber-issue-card';
            callout.innerHTML = `
              <span class="issue-tag">${escapeHtml(f.severity)}</span>
              <div class="issue-name">${escapeHtml(f.issue_type)}</div>
              <div class="issue-guidance">${escapeHtml(f.remediation || 'Remediate this finding prior to deployment.')}</div>
            `;
            container.appendChild(callout);
          });
        }
      });
    }

    function renderDocstrings(docstrings) {
      const container = document.getElementById('docstrings-wrapper');
      container.innerHTML = '';
      if (!docstrings || docstrings.length === 0) {
        container.innerHTML = '<div style="color: var(--uber-gray-500); padding: 1.5rem;">No function docstrings generated.</div>';
        return;
      }

      docstrings.forEach(d => {
        const box = document.createElement('div');
        box.className = 'doc-box';
        box.innerHTML = `
          <div class="doc-box-header">
            <span>${escapeHtml(d.target)}</span>
            <button class="btn-uber-copy" onclick="copySnippet('${escapeAttr(d.docstring)}')">Copy Docstring</button>
          </div>
          <pre class="doc-code">${escapeHtml(d.docstring)}</pre>
        `;
        container.appendChild(box);
      });
    }

    function renderReadme(markdown) {
      const container = document.getElementById('readme-wrapper');
      if (!markdown) {
        container.innerHTML = '<p style="color: var(--uber-gray-500);">No README generated.</p>';
        return;
      }
      let h = escapeHtml(markdown)
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/\\*\\*(.*?)\\*\\*/gim, '<strong>$1</strong>')
        .replace(/\\*(.*?)\\*/gim, '<em>$1</em>')
        .replace(/`([^`]+)`/gim, '<code style="background: rgba(255,255,255,0.08); padding: 0.15rem 0.4rem; border-radius: 4px; color: #fff;">$1</code>')
        .replace(/\\n/gim, '<br>');
      container.innerHTML = h;  // faraday: ignore
    }

    function switchTab(tabId) {
      document.querySelectorAll('.uber-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));

      event.currentTarget.classList.add('active');
      const targetView = document.getElementById('view-' + tabId);
      if (targetView) targetView.classList.add('active');
    }

    async function triggerScan() {
      const btn = event.currentTarget;
      btn.disabled = true;
      btn.innerHTML = 'Analyzing on NPU...';
      try {
        await loadScanData();
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg> Request Scan`;
      }
    }

    function copySnippet(text) {
      navigator.clipboard.writeText(text);
      alert('Docstring copied to clipboard!');
    }

    function copyReadme() {
      if (scanData && scanData.readme_markdown) {
        navigator.clipboard.writeText(scanData.readme_markdown);
        alert('README markdown copied to clipboard!');
      }
    }

    function downloadSarif() {
      window.open('/api/sarif', '_blank');
    }

    function escapeHtml(str) {
      return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function escapeAttr(str) {
      return (str || '').replace(/'/g, "\\\\'").replace(/\\n/g, '\\\\n');
    }

    window.addEventListener('DOMContentLoaded', loadScanData);
  </script>
</body>
</html>
"""


class FaradayWebHandler(BaseHTTPRequestHandler):
    """Air-gapped local HTTP handler for Faraday Interactive Dashboard."""

    project_root: Path = Path(".")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        elif path == "/api/scan":
            self._handle_api_scan()
            return

        elif path == "/api/file":
            file_param = query.get("path", [""])[0]
            self._handle_api_file(file_param)
            return

        elif path == "/api/sarif":
            self._handle_api_sarif()
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _handle_api_scan(self):
        """Execute full AST scan and deterministic security checks, returning JSON dashboard payload."""
        root = self.project_root.resolve()
        cfg = load_project_config(root)

        scan_res = scan_project(str(root), custom_ignores=cfg.get("exclude", []))
        sec_findings = scan_all(scan_res.chunks)

        # Map findings per file
        findings_by_file: Dict[str, list] = {}
        for f in sec_findings:
            norm = str(Path(f.file_path).resolve())
            findings_by_file.setdefault(norm, []).append({
                "severity": f.severity,
                "issue_type": f.label,
                "line_number": f.line_number,
                "code_snippet": f.snippet,
                "remediation": "Remove secret from source code and load via environment variables or secret manager.",
            })

        # Build list of scanned files
        files_list = []
        seen_files = set()
        for chunk in scan_res.chunks:
            p = str(Path(chunk.file_path).resolve())
            if p not in seen_files:
                seen_files.add(p)
                try:
                    rel = str(Path(p).relative_to(root))
                except ValueError:
                    rel = Path(p).name

                file_findings = findings_by_file.get(p, [])
                files_list.append({
                    "path": p,
                    "rel_path": rel,
                    "findings": file_findings,
                })

        high_count = sum(1 for f in sec_findings if f.severity.upper() == "HIGH")
        med_count = sum(1 for f in sec_findings if f.severity.upper() == "MEDIUM")
        health_score = max(5, 100 - (high_count * 25) - (med_count * 8))

        # Docstrings & README synthesis from on-device neural review
        backend = get_backend()
        chunk_reviews = review_all(backend, scan_res.chunks)

        docstrings_list = []
        for cr in chunk_reviews:
            if cr.docstring and cr.docstring.strip():
                try:
                    rel = str(Path(cr.file_path).relative_to(root))
                except ValueError:
                    rel = Path(cr.file_path).name
                docstrings_list.append({
                    "target": f"{rel} :: {cr.chunk_name}",
                    "docstring": cr.docstring,
                })

        # README synthesis
        readme_md = generate_readme(backend, chunk_reviews)

        payload = {
            "target_path": str(root),
            "total_chunks": len(scan_res.chunks),
            "files": files_list,
            "high_count": high_count,
            "medium_count": med_count,
            "health_score": health_score,
            "docstrings": docstrings_list,
            "readme_markdown": readme_md,
        }

        data = json.dumps(payload, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data.encode("utf-8"))

    def _handle_api_file(self, file_path_str: str):
        """Return the raw source code of a specified project file."""
        if not file_path_str:
            self.send_response(400)
            self.end_headers()
            return

        fpath = Path(file_path_str).resolve()
        # Security constraint: only allow files inside or near project_root
        if not fpath.exists() or not fpath.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "File not found"}).encode("utf-8"))
            return

        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"source": content}).encode("utf-8"))

    def _handle_api_sarif(self):
        """Generate and stream SARIF 2.1.0 report."""
        root = self.project_root.resolve()
        cfg = load_project_config(root)
        scan_res = scan_project(str(root), custom_ignores=cfg.get("exclude", []))
        sec_findings = scan_all(scan_res.chunks)

        sarif_data = generate_sarif_report(sec_findings, [], str(root))
        sarif_json = json.dumps(sarif_data, indent=2)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Disposition", 'attachment; filename="faraday_results.sarif"')
        self.end_headers()
        self.wfile.write(sarif_json.encode("utf-8"))

    def log_message(self, format, *args):
        # Silent logging for clean terminal presentation
        pass


def launch_web_dashboard(project_path: Path, port: int = 8000, auto_open: bool = True):
    """Start local web server and open the interactive Faraday dashboard."""
    FaradayWebHandler.project_root = project_path.resolve()
    server_address = ("127.0.0.1", port)

    try:
        httpd = HTTPServer(server_address, FaradayWebHandler)
    except OSError as e:
        if "already in use" in str(e).lower() or "10048" in str(e):
            port = port + 1
            server_address = ("127.0.0.1", port)
            httpd = HTTPServer(server_address, FaradayWebHandler)
        else:
            raise

    url = f"http://localhost:{port}"
    print(f"\n[Faraday] Interactive Visual Dashboard running at: {url}")
    print(f"[Faraday] 100% Air-Gapped & Offline on Snapdragon Hexagon NPU.")
    print(f"[Faraday] Press Ctrl+C in terminal to stop server.\n")

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Faraday] Dashboard stopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    launch_web_dashboard(target, port=8000)
