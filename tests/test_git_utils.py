from pathlib import Path
from backend.core.git_utils import find_git_root, install_pre_commit_hook


def test_find_git_root():
    # Workspace is a git repo
    root = find_git_root(Path("."))
    assert root is not None
    assert (root / ".git").exists()


def test_install_pre_commit_hook(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    hook_file = install_pre_commit_hook(tmp_path)
    assert hook_file.exists()
    content = hook_file.read_text(encoding="utf-8")
    assert "faraday --staged --fail-on HIGH" in content
