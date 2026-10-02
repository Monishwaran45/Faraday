"""
test_linux_compatibility.py

Validates Linux cross-platform compatibility for Faraday:
1. Linux SoC & Qualcomm CPU detection (/proc/cpuinfo, /sys/devices/soc0/).
2. Linux dynamic library discovery (LD_LIBRARY_PATH, libQnnHtp.so).
3. POSIX shell pre-commit hook generation and executable permissions.
4. POSIX path resolution across file scanning and chunking.

Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import os
import stat
import platform
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
from backend.models.verify_npu import probe_hardware_environment
from backend.core.doctor import check_npu_silicon
from backend.core.git_utils import install_pre_commit_hook
from backend.core.file_scanner import CodeChunk
from backend.core.secret_scanner import scan_chunk


def test_linux_hardware_probe_qualcomm_soc(tmp_path):
    """Verifies that Linux Qualcomm SoC sysfs is recognized as Snapdragon."""
    mock_soc_machine = "Snapdragon X Elite (sc8380xp)"

    with patch("platform.system", return_value="Linux"), \
         patch("platform.machine", return_value="aarch64"), \
         patch("platform.processor", return_value="aarch64"), \
         patch.object(Path, "exists") as mock_exists, \
         patch.object(Path, "read_text", return_value=mock_soc_machine):

        mock_exists.return_value = True
        hw = probe_hardware_environment()

        assert hw["os"] == "Linux"
        assert hw["machine"] == "aarch64"
        assert hw["is_arm64"] is True
        assert hw["is_snapdragon"] is True
        assert "Snapdragon" in hw["soc_model"]


def test_linux_hardware_probe_generic_x86():
    """Verifies that generic Linux x86_64 falls back gracefully to CPU mode."""
    with patch("platform.system", return_value="Linux"), \
         patch("platform.machine", return_value="x86_64"), \
         patch("platform.processor", return_value="x86_64"), \
         patch.object(Path, "exists", return_value=False):

        hw = probe_hardware_environment()

        assert hw["os"] == "Linux"
        assert hw["is_arm64"] is False
        assert hw["is_snapdragon"] is False


def test_linux_ld_library_path_qnn_discovery(tmp_path, monkeypatch):
    """Verifies that QNN shared libraries (.so) in LD_LIBRARY_PATH are discovered."""
    fake_lib_dir = tmp_path / "lib"
    fake_lib_dir.mkdir(parents=True)
    fake_so = fake_lib_dir / "libQnnHtp.so"
    fake_so.write_text("fake elf binary")

    monkeypatch.setenv("LD_LIBRARY_PATH", str(fake_lib_dir))

    info = check_npu_silicon()
    found = [Path(p).name for p in info.get("found_qnn_libs", [])]
    assert "libQnnHtp.so" in found


def test_posix_pre_commit_hook_structure(tmp_path):
    """Verifies that install_pre_commit_hook creates a POSIX-compliant /bin/sh hook."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    hook_path = install_pre_commit_hook(tmp_path)
    assert hook_path.exists()
    content = hook_path.read_text(encoding="utf-8")

    assert content.startswith("#!/bin/sh")
    assert "faraday --staged --fail-on HIGH" in content


def test_posix_path_handling_in_scanner():
    """Verifies that forward-slash POSIX paths are seamlessly handled in findings."""
    posix_path = "src/services/auth_handler.py"
    chunk = CodeChunk(
        file_path=posix_path,
        language="python",
        name="test_func",
        start_line=1,
        end_line=3,
        code='import os\nos.system("rm -rf " + user_input)'
    )
    findings = scan_chunk(chunk)
    assert len(findings) > 0
    assert findings[0].file_path == posix_path
