"""
llm_reviewer.py

Runs each code chunk through the model backend for:
  1. Bug/style/security review
  2. Docstring generation

And separately builds a README from the full set of chunk summaries.

Prompts are intentionally strict about output format so report_builder.py
can parse them reliably without needing the model to emit JSON (small
on-device models are often unreliable at strict JSON; a fixed text format
with clear section headers is more robust).
"""

from dataclasses import dataclass


REVIEW_PROMPT_TEMPLATE = """You are a senior code reviewer. Analyze the following {language} code for:
- Logic bugs or edge cases
- Security issues (injection, unsafe deserialization, hardcoded secrets, unsafe eval/exec)
- Style/readability issues per common {language} conventions

Code:
{code}

Respond in exactly this format, nothing else:
ISSUES:
<numbered list, or "None found">
SEVERITY:
<Low/Medium/High per issue, or "N/A">
SUGGESTED_FIX:
<brief fix per issue, or "N/A">
"""

DOCSTRING_PROMPT_TEMPLATE = """Write a concise docstring for the following {language} function/class.
Describe purpose, parameters, return value, and any exceptions raised.
Output ONLY the docstring text, no explanation, no code fences.

Code:
{code}
"""

README_PROMPT_TEMPLATE = """Given the following list of module/function summaries from a codebase,
write a professional README.md including: project purpose (inferred),
setup instructions (if detectable from imports/dependencies), and a
brief architecture overview. Output only the README content in Markdown.

Summaries:
{summaries}
"""


@dataclass
class ChunkReview:
    file_path: str
    chunk_name: str
    start_line: int
    end_line: int
    review_raw: str
    docstring: str


def review_chunk(backend, chunk) -> ChunkReview:
    review_prompt = REVIEW_PROMPT_TEMPLATE.format(language=chunk.language, code=chunk.code)
    review_raw = backend.generate(review_prompt)

    # Only generate docstrings for named functions and classes, not configs or fallback blocks
    should_gen_doc = (
        chunk.name not in ("<config>", "<module_level>")
        and not chunk.name.startswith("block_")
        and chunk.language not in ("json", "yaml", "toml", "sql", "config")
    )
    docstring = ""
    if should_gen_doc:
        doc_prompt = DOCSTRING_PROMPT_TEMPLATE.format(language=chunk.language, code=chunk.code)
        docstring = backend.generate(doc_prompt).strip()

    return ChunkReview(
        file_path=chunk.file_path,
        chunk_name=chunk.name,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        review_raw=review_raw.strip(),
        docstring=docstring,
    )


def review_all(backend, chunks) -> list:
    # Omit static data/config files from code review
    code_chunks = [c for c in chunks if c.name != "<config>" and c.language not in ("json", "yaml", "toml", "config")]
    return [review_chunk(backend, c) for c in code_chunks]


def generate_readme(backend, chunk_reviews: list) -> str:
    # Build a compact summary string from chunk names/locations rather than
    # dumping every review verbatim, to keep the README prompt short.
    summary_lines = [
        f"- {cr.file_path}::{cr.chunk_name} (lines {cr.start_line}-{cr.end_line})"
        for cr in chunk_reviews
    ]
    prompt = README_PROMPT_TEMPLATE.format(summaries="\n".join(summary_lines))
    return backend.generate(prompt, max_tokens=1024).strip()
