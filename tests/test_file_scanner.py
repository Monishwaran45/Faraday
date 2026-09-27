import pytest
from pathlib import Path
from backend.core.file_scanner import (
    _chunk_python_file,
    _chunk_javascript_file,
    _chunk_by_lines,
    scan_project,
)

def test_chunk_python_file_captures_functions_and_classes(tmp_path):
    code = """
import os

API_KEY = "dummy_secret"

def calculate_total(a, b):
    return a + b

class InventoryManager:
    def __init__(self):
        self.items = []
"""
    file_path = tmp_path / "test_module.py"
    file_path.write_text(code.strip(), encoding="utf-8")

    chunks = _chunk_python_file(file_path, code.strip())
    chunk_names = [c.name for c in chunks]

    assert "calculate_total" in chunk_names
    assert "InventoryManager" in chunk_names
    # Module level code (API_KEY) must be captured and not skipped!
    assert "<module_level>" in chunk_names


def test_chunk_javascript_file_captures_functions_and_classes(tmp_path):
    js_code = """
function calculateETA(distance, speed) {
    if (speed <= 0) return 0;
    return distance / speed;
}

const renderCharts = (data) => {
    console.log("rendering", data);
};

class DashboardController {
    constructor() {
        this.active = true;
    }
}
"""
    file_path = tmp_path / "app.js"
    file_path.write_text(js_code.strip(), encoding="utf-8")

    chunks = _chunk_javascript_file(file_path, js_code.strip(), "javascript")
    names = [c.name for c in chunks]

    assert "calculateETA" in names
    assert "renderCharts" in names
    assert "DashboardController" in names


def test_scan_project_config_files(tmp_path):
    config_file = tmp_path / "vercel.json"
    config_file.write_text('{"builds": [{"src": "app.py", "use": "@vercel/python"}]}', encoding="utf-8")

    res = scan_project(str(tmp_path))
    assert res.files_scanned == 1
    assert len(res.chunks) == 1
    assert res.chunks[0].name == "<config>"


def test_chunk_by_lines_fallback(tmp_path):
    code = "\n".join([f"line {i}" for i in range(250)])
    file_path = tmp_path / "sample.txt"
    file_path.write_text(code, encoding="utf-8")

    chunks = _chunk_by_lines(file_path, code, "text")
    assert len(chunks) >= 2
    assert chunks[0].start_line == 1
    assert "block_1" in chunks[0].name
