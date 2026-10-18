from pathlib import Path

import pytest

from backend.core.proof_of_fix import PatchError, apply_patch, propose_patch


def test_proposal_is_review_only_and_contains_diff(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("query = \"SELECT * FROM users WHERE id = \" + user_id\n", encoding="utf-8")
    replacement = "query = \"SELECT * FROM users WHERE id = ?\"\ncursor.execute(query, (user_id,))\n"

    proposal = propose_patch(tmp_path, "app.py", replacement)

    assert "--- a/app.py" in proposal.diff
    assert "+++ b/app.py" in proposal.diff
    assert target.read_text(encoding="utf-8").startswith("query = ")
    with pytest.raises(PatchError, match="approval"):
        apply_patch(tmp_path, proposal)


def test_approved_patch_applies_and_returns_hash(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("before\n", encoding="utf-8")
    proposal = propose_patch(tmp_path, "app.py", "after\n")

    digest = apply_patch(tmp_path, proposal, approved=True)

    assert target.read_text(encoding="utf-8") == "after\n"
    assert len(digest) == 64


def test_conflict_detected_if_file_changed_after_preview(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("before\n", encoding="utf-8")
    proposal = propose_patch(tmp_path, "app.py", "after\n")
    target.write_text("someone else's change\n", encoding="utf-8")

    with pytest.raises(PatchError, match="changed"):
        apply_patch(tmp_path, proposal, approved=True)


@pytest.mark.parametrize("path", ["../outside.py", "/tmp/outside.py", ""])
def test_rejects_paths_outside_project(tmp_path: Path, path: str):
    with pytest.raises(PatchError):
        propose_patch(tmp_path, path, "replacement\n")


def test_rejects_symlink_target(tmp_path: Path):
    outside = tmp_path.parent / "outside-faraday-test.py"
    outside.write_text("private\n", encoding="utf-8")
    link = tmp_path / "linked.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable in this environment")

    with pytest.raises(PatchError, match="symbolic link"):
        propose_patch(tmp_path, "linked.py", "changed\n")
