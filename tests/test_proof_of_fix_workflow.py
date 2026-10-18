from pathlib import Path

from rich.console import Console

from backend.core.proof_of_fix_workflow import run_proof_of_fix


VULNERABLE = 'user_id = input("id: ")\nquery = "SELECT * FROM users WHERE id = " + user_id\n'
FIXED = 'user_id = input("id: ")\nquery = "SELECT * FROM users WHERE id = ?"\ncursor.execute(query, (user_id,))\n'


def test_declining_preview_does_not_modify_target(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text(VULNERABLE, encoding="utf-8")
    console = Console(record=True, width=120)

    code = run_proof_of_fix(tmp_path, "app.py", FIXED, approve=lambda: False, console=console)

    assert code == 1
    assert target.read_text(encoding="utf-8") == VULNERABLE
    assert "Proposed patch" in console.export_text()
    assert "declined" in console.export_text()


def test_approval_applies_patch_and_rescans(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text(VULNERABLE, encoding="utf-8")
    console = Console(record=True, width=120)

    code = run_proof_of_fix(tmp_path, "app.py", FIXED, approve=lambda: True, console=console)

    assert code == 0
    assert target.read_text(encoding="utf-8") == FIXED
    output = console.export_text()
    assert "Findings in app.py" in output
    assert "Rescan complete" in output
    assert "original finding signatures were not reproduced" in output


def test_clean_file_is_not_patched(tmp_path: Path):
    target = tmp_path / "app.py"
    clean = 'query = "SELECT * FROM users WHERE id = ?"\n'
    target.write_text(clean, encoding="utf-8")
    console = Console(record=True, width=120)

    code = run_proof_of_fix(
        tmp_path, "app.py", clean + "# reviewed\n", approve=lambda: True, console=console
    )

    assert code == 2
    assert target.read_text(encoding="utf-8") == clean
