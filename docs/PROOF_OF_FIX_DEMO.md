# Faraday Proof-of-Fix demo

This demo illustrates a narrow, testable building block for the scan → review → approve → rescan workflow. It does not claim to generate secure fixes automatically: a caller supplies replacement text, and a human reviews the diff before approving it.

## Run the tests

```bash
python -m pytest tests/test_proof_of_fix.py -q
```

## Example

```python
from pathlib import Path
from backend.core.proof_of_fix import propose_patch, apply_patch

project = Path(".")
proposal = propose_patch(
    project,
    "demo/sample_project/database.py",
    Path("demo/sample_project/database.py").read_text(encoding="utf-8")
        .replace(
            'query = "SELECT * FROM users WHERE id = " + user_id',
            'query = "SELECT * FROM users WHERE id = ?"\n    cursor.execute(query, (user_id,))',
        ),
)
print(proposal.diff)  # Show this diff to the user for review.
# Only after explicit user approval:
# apply_patch(project, proposal, approved=True)
```

Review the proposed diff before applying it. The apply operation rejects path traversal, symlinked targets, missing files, and stale proposals when the target changed after preview. The caller must still validate that the proposed code is semantically correct and run relevant tests after applying it.

## Current scope and limitations

- UTF-8 text files only; binary files are rejected.
- One existing file per proposal.
- Approval is a boolean supplied by the calling application; the UI must obtain it from an explicit user action.
- This module does not scan code, synthesize patches, execute code, or independently prove a vulnerability is fixed.
- A successful write is not proof of a secure fix. Rescan and test the result.
