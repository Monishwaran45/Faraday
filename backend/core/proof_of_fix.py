"""Human-reviewed, conflict-safe code patch workflow for Faraday.

This module intentionally does not generate patches or execute scanned code. Callers
must supply a proposed replacement and obtain explicit approval before applying it.
"""
from __future__ import annotations

from dataclasses import dataclass
import difflib
import hashlib
import os
from pathlib import Path


class PatchError(ValueError):
    """Raised when a patch cannot be safely previewed or applied."""


@dataclass(frozen=True)
class PatchProposal:
    relative_path: str
    original_sha256: str
    replacement_text: str
    diff: str


def _resolve_target(root: str | Path, relative_path: str) -> tuple[Path, Path]:
    root_path = Path(root).resolve()
    rel = Path(relative_path)
    if rel.is_absolute() or not relative_path or any(part == ".." for part in rel.parts):
        raise PatchError("Target must be a non-empty path contained inside the project root.")
    candidate = root_path / rel
    # Reject symlinked path components, even if they currently resolve inside root.
    current = root_path
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise PatchError("Refusing to patch a path containing a symbolic link.")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root_path):
        raise PatchError("Target resolves outside the project root.")
    if not resolved.exists() or not resolved.is_file():
        raise PatchError("Target must be an existing regular file.")
    return root_path, resolved


def propose_patch(
    root: str | Path,
    relative_path: str,
    replacement_text: str,
) -> PatchProposal:
    """Create a review-only patch proposal for an existing project file."""
    _, target = _resolve_target(root, relative_path)
    if not isinstance(replacement_text, str):
        raise PatchError("Replacement content must be text.")
    try:
        original = target.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise PatchError("Target must be a readable UTF-8 text file.") from exc
    if original == replacement_text:
        raise PatchError("Replacement is identical to the current file.")
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            replacement_text.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )
    return PatchProposal(
        relative_path=relative_path,
        original_sha256=hashlib.sha256(original.encode("utf-8")).hexdigest(),
        replacement_text=replacement_text,
        diff=diff,
    )


def apply_patch(
    root: str | Path,
    proposal: PatchProposal,
    *,
    approved: bool = False,
) -> str:
    """Apply a reviewed proposal only with explicit approval and no file conflict.

    Returns the SHA-256 of the written content. Uses a same-directory temporary
    file and atomic replace to avoid leaving a partially written target.
    """
    if not approved:
        raise PatchError("Patch not applied: explicit user approval is required.")
    _, target = _resolve_target(root, proposal.relative_path)
    try:
        current = target.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise PatchError("Target is no longer a readable UTF-8 text file.") from exc
    current_hash = hashlib.sha256(current.encode("utf-8")).hexdigest()
    if current_hash != proposal.original_sha256:
        raise PatchError("Patch conflict: file changed after the proposal was created.")
    new_bytes = proposal.replacement_text.encode("utf-8")
    temp_path: Path | None = None
    try:
        import tempfile
        fd, temp_name = tempfile.mkstemp(prefix=".faraday-patch-", dir=target.parent)
        temp_path = Path(temp_name)
        with os.fdopen(fd, "wb") as stream:
            stream.write(new_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        # Preserve the target's permission bits.
        os.chmod(temp_path, target.stat().st_mode & 0o777)
        os.replace(temp_path, target)
    except OSError as exc:
        raise PatchError(f"Could not safely write patch: {exc}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
    return hashlib.sha256(new_bytes).hexdigest()
