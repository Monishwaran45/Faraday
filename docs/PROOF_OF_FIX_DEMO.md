# Faraday Proof-of-Fix demo

Proof-of-Fix now has an interactive scan → review → approve → rescan command. It scans the selected file with Faraday's existing static security scanner, displays findings and a unified diff, and only writes after an explicit confirmation. It does not invent replacement code or claim that a successful write proves a secure fix.

## Install / update the command

From the Faraday repository:

```bash
python -m pip install -e .
```

## Run the end-to-end workflow

Create a UTF-8 text file containing the **complete proposed contents** of the file you want to fix, then run:

```bash
faraday-fix . path/to/vulnerable_file.py --replacement-file path/to/proposed_file.py
```

On Windows, if the script is not on PATH, run:

```powershell
python -m backend.proof_of_fix_cli . path\to\vulnerable_file.py --replacement-file path\to\proposed_file.py
```

The command:
1. Scans the selected target file with Faraday's current static scanner.
2. Stops without changing anything if no findings are detected.
3. Prints the findings and proposed unified diff.
4. Asks for confirmation (default is **No**).
5. Applies the replacement only after approval and only if the original file has not changed since preview.
6. Re-scans the target and reports whether the original finding signatures are still detected.

The replacement file is a proposal supplied by the developer; Faraday does not generate it. Review the diff carefully, run the relevant test suite, and independently verify the fix. A clean rescan is evidence that those scanner signatures were not reproduced, not proof that the code is secure.

## Run tests

```bash
python -m pytest tests/test_proof_of_fix.py tests/test_proof_of_fix_workflow.py -v
python -m pytest -v
```

## Security notes

- UTF-8 text files only; binary files are rejected.
- One existing file per proposal.
- Empty paths, traversal, symlinked paths, missing targets, and stale proposals are rejected.
- Declining approval leaves the target unchanged.
- Never use an unreviewed replacement. Run project tests and a fresh scan after applying.
