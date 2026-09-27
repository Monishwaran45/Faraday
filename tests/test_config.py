from pathlib import Path
from backend.core.config import load_project_config, init_project_config, DEFAULT_CONFIG


def test_load_default_config(tmp_path):
    cfg = load_project_config(tmp_path)
    assert cfg["output"] == "./review_output"
    assert "tests/**" in cfg["exclude"]
    assert cfg["skip_ai"] is False


def test_init_project_config(tmp_path):
    cfg_file = init_project_config(tmp_path)
    assert cfg_file.exists()
    assert ".faraday.yml" in cfg_file.name

    loaded = load_project_config(tmp_path)
    assert loaded["fail_on"] == "HIGH"
    assert loaded["output"] == "./review_output"


def test_load_json_config(tmp_path):
    json_file = tmp_path / ".faraday.json"
    json_file.write_text('{"fail_on": "LOW", "skip_ai": true}', encoding="utf-8")

    loaded = load_project_config(tmp_path)
    assert loaded["fail_on"] == "LOW"
    assert loaded["skip_ai"] is True
