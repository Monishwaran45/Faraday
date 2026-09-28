"""
file_scanner.py

Walks a project directory, finds source files, and splits each file into
reviewable chunks (roughly: top-level functions/classes, with a fallback
to fixed-size line blocks for languages/files we don't parse deeply).

This is intentionally dependency-light (stdlib only) so it runs anywhere,
including inside an air-gapped environment with no pip access.
"""

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import fnmatch

# Extensions we'll scan. Add more as needed.
SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".sh": "bash",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
}

# Directories and patterns we never want to walk into in real projects.
IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv", "env", ".env",
    "dist", "build", ".idea", ".vscode", "target", "coverage", ".pytest_cache",
    ".qaihm", ".qai_hub", "vendor", "bin", "obj", ".next", ".nuxt",
}

IGNORED_PATTERNS = {
    "*.min.js", "*.bundle.js", "*.min.css", "*.map", "*.lock", "*.sum",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "uv.lock",
}

MAX_FILE_SIZE_BYTES = 1_048_576  # 1 MB safety limit for real production files
MAX_CHUNK_LINES = 120  # fallback chunk size for non-Python / unparsed files


@dataclass
class CodeChunk:
    file_path: str
    language: str
    name: str          # function/class name, or "block_N" for fallback chunks
    start_line: int
    end_line: int
    code: str


@dataclass
class ScanResult:
    files_scanned: int = 0
    chunks: list = field(default_factory=list)



def _load_gitignore_patterns(root: Path) -> list:
    """Read .gitignore patterns from root directory if present."""
    patterns = []
    gitignore_path = root / ".gitignore" if root.is_dir() else root.parent / ".gitignore"
    if gitignore_path.exists():
        try:
            for line in gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)
        except Exception:
            pass
    return patterns


def _is_ignored(path: Path, root: Path, gitignore_patterns: list, custom_ignores: list = None) -> bool:
    """Check if file should be ignored based on default rules, gitignore, and custom flags."""
    fname = path.name
    try:
        rel_path = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        rel_path = fname

    norm_path = str(path).replace("\\", "/")

    # Check ignored patterns (minified, lockfiles, etc.)
    for pattern in IGNORED_PATTERNS:
        if fnmatch.fnmatch(fname, pattern):
            return True

    # Check custom ignore patterns
    if custom_ignores:
        for pattern in custom_ignores:
            norm_pat = pattern.replace("\\", "/").rstrip("/")
            if (
                fnmatch.fnmatch(fname, norm_pat)
                or fnmatch.fnmatch(rel_path, norm_pat)
                or fnmatch.fnmatch(rel_path, f"{norm_pat}/*")
                or fnmatch.fnmatch(rel_path, f"{norm_pat}/**")
                or fnmatch.fnmatch(norm_path, norm_pat)
                or any(fnmatch.fnmatch(part, norm_pat) for part in path.parts)
            ):
                return True

    # Check gitignore patterns
    for pat in gitignore_patterns:
        cleaned_pat = pat.rstrip("/").replace("\\", "/")
        if fnmatch.fnmatch(rel_path, cleaned_pat) or fnmatch.fnmatch(fname, cleaned_pat) or fnmatch.fnmatch(rel_path, f"*/{cleaned_pat}"):
            return True

    return False


def _iter_source_files(
    root: Path,
    custom_ignores: list = None,
    only_files: list = None,
    max_file_size_kb: int = 1024,
):
    """Walk directory or yield targeted files, respecting gitignore and safety constraints."""
    max_bytes = max_file_size_kb * 1024
    gitignore_patterns = _load_gitignore_patterns(root)

    if only_files is not None:
        for f in only_files:
            fpath = Path(f).resolve()
            if not fpath.exists() or not fpath.is_file():
                continue
            if fpath.suffix not in SUPPORTED_EXTENSIONS:
                continue
            if fpath.stat().st_size > max_bytes:
                continue
            if _is_ignored(fpath, root, gitignore_patterns, custom_ignores):
                continue
            yield fpath
        return

    if root.is_file():
        if root.suffix in SUPPORTED_EXTENSIONS and root.stat().st_size <= max_bytes:
            yield root
        return

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in IGNORED_DIRS and not d.startswith(".")
            and not any(fnmatch.fnmatch(d, pat.rstrip("/")) for pat in gitignore_patterns)
            and not (custom_ignores and any(fnmatch.fnmatch(d, pat.replace("\\", "/").rstrip("/")) for pat in custom_ignores))
        ]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in SUPPORTED_EXTENSIONS:
                if fpath.stat().st_size > max_bytes:
                    continue
                if _is_ignored(fpath, root, gitignore_patterns, custom_ignores):
                    continue
                yield fpath


def _chunk_python_file(path: Path, source: str) -> list:
    """Use the ast module to split a Python file into function/class-level chunks."""
    chunks = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _chunk_by_lines(path, source, "python")

    lines = source.splitlines()
    top_level_nodes = [
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]

    if not top_level_nodes:
        return _chunk_by_lines(path, source, "python")

    # Module-level statements (imports, constants, config values, etc.) live
    # OUTSIDE any function/class node and must not be silently dropped —
    # this is exactly where hardcoded secrets/config tend to live.
    covered_lines = set()
    for node in top_level_nodes:
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        code = "\n".join(lines[start - 1:end])
        chunks.append(CodeChunk(
            file_path=str(path),
            language="python",
            name=node.name,
            start_line=start,
            end_line=end,
            code=code,
        ))
        covered_lines.update(range(start, end + 1))

    module_level_lines = [
        (i + 1, line) for i, line in enumerate(lines)
        if (i + 1) not in covered_lines and line.strip()
    ]
    if module_level_lines:
        start = module_level_lines[0][0]
        end = module_level_lines[-1][0]
        code = "\n".join(lines[start - 1:end])
        chunks.append(CodeChunk(
            file_path=str(path),
            language="python",
            name="<module_level>",
            start_line=start,
            end_line=end,
            code=code,
        ))

    return chunks


def _chunk_javascript_file(path: Path, source: str, language: str) -> list:
    """Extract top-level functions and classes from JavaScript/TypeScript source."""
    lines = source.splitlines()
    chunks = []
    covered_lines = set()

    # Pattern matching top-level functions, arrow functions, and classes
    pattern = re.compile(
        r'^(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\('
        r'|^(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>'
        r'|^(?:export\s+(?:default\s+)?)?class\s+([a-zA-Z0-9_$]+)'
    )

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        m = pattern.match(stripped)
        if m:
            fn_name = m.group(1) or m.group(2) or m.group(3) or "anonymous"
            start_line = i + 1
            brace_count = 0
            found_opening = False
            end_line = start_line

            for j in range(i, len(lines)):
                curr_line = lines[j]
                for char in curr_line:
                    if char == '{':
                        brace_count += 1
                        found_opening = True
                    elif char == '}':
                        brace_count -= 1
                if found_opening and brace_count <= 0:
                    end_line = j + 1
                    break

            if end_line >= start_line:
                func_code = "\n".join(lines[start_line - 1:end_line])
                chunks.append(CodeChunk(
                    file_path=str(path),
                    language=language,
                    name=fn_name,
                    start_line=start_line,
                    end_line=end_line,
                    code=func_code,
                ))
                covered_lines.update(range(start_line, end_line + 1))
                i = max(i + 1, end_line)
                continue
        i += 1

    if chunks:
        # If functions were parsed, bundle top-level imports/constants into a single <module_level> chunk
        module_lines = [
            line for idx, line in enumerate(lines)
            if (idx + 1) not in covered_lines and line.strip()
        ]
        if module_lines:
            chunks.append(CodeChunk(
                file_path=str(path),
                language=language,
                name="<module_level>",
                start_line=1,
                end_line=len(lines),
                code="\n".join(module_lines[:MAX_CHUNK_LINES]),
            ))
        return chunks

    return _chunk_by_lines(path, source, language)


def _chunk_by_lines(path: Path, source: str, language: str) -> list:
    """Fallback: fixed-size line blocks. Used for non-Python/JS files or unparsable code."""
    lines = source.splitlines()
    chunks = []
    for i in range(0, len(lines), MAX_CHUNK_LINES):
        block = lines[i:i + MAX_CHUNK_LINES]
        if not any(line.strip() for line in block):
            continue
        chunks.append(CodeChunk(
            file_path=str(path),
            language=language,
            name=f"block_{i // MAX_CHUNK_LINES + 1}",
            start_line=i + 1,
            end_line=i + len(block),
            code="\n".join(block),
        ))
    return chunks


def scan_project(
    root_dir: str,
    custom_ignores: list = None,
    only_files: list = None,
    max_file_size_kb: int = 1024,
) -> ScanResult:
    root = Path(root_dir)
    result = ScanResult()

    for file_path in _iter_source_files(
        root,
        custom_ignores=custom_ignores,
        only_files=only_files,
        max_file_size_kb=max_file_size_kb,
    ):
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        if not source.strip():
            continue

        language = SUPPORTED_EXTENSIONS.get(file_path.suffix, "text")
        result.files_scanned += 1

        # Configuration and data files: chunk as <config> (scanned for secrets, skipped from docstrings)
        if language in ("json", "yaml", "toml", "sql"):
            lines = source.splitlines()
            file_chunks = [CodeChunk(
                file_path=str(file_path),
                language=language,
                name="<config>",
                start_line=1,
                end_line=max(1, len(lines)),
                code=source,
            )]
        elif language == "python":
            file_chunks = _chunk_python_file(file_path, source)
        elif language in ("javascript", "typescript"):
            file_chunks = _chunk_javascript_file(file_path, source, language)
        else:
            file_chunks = _chunk_by_lines(file_path, source, language)

        result.chunks.extend(file_chunks)

    return result


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    res = scan_project(target)
    print(f"Scanned {res.files_scanned} files, produced {len(res.chunks)} chunks.")
    for c in res.chunks[:5]:
        print(f"  {c.file_path}::{c.name} (lines {c.start_line}-{c.end_line})")
