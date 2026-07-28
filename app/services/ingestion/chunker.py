"""
Chunking stage: elements -> chunks (per blueprint §13).

Two responsibilities, deliberately kept separate:
1. Heading tracking (custom, ~15 lines): walks elements maintaining a
   breadcrumb of active headings — this is specific to our citation format
   (`heading_path` shown next to every citation), so it stays hand-rolled.
2. Packing paragraphs into token-budgeted, overlapping chunks: delegated to
   LangChain's `RecursiveCharacterTextSplitter`, which is the standard tool
   for this — it splits on paragraph/sentence/word boundaries in that
   priority order rather than naive fixed-size slicing.

`CHUNKER_VERSION` is stored on every DocumentVersion so chunking
experiments are reproducible and comparable across index builds.
"""
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.services.ingestion.parser import Element

CHUNKER_VERSION = "v2-langchain-recursive-structure-aware"

# Rough chars-per-token estimate for English text; avoids taking a hard
# dependency on a tokenizer just to size the splitter.
_CHARS_PER_TOKEN = 4


@dataclass
class ChunkDraft:
    text: str
    heading_path: str | None
    page_start: int | None
    page_end: int | None
    token_count: int


@dataclass
class _Section:
    """One contiguous run of paragraphs under the same heading path."""
    heading_path: str | None
    paragraphs: list[str]
    page_start: int | None
    page_end: int | None


def _group_into_sections(elements: list[Element]) -> list[_Section]:
    sections: list[_Section] = []
    heading_stack: list[tuple[int, str]] = []  # (level, text)
    current: _Section | None = None

    def heading_path() -> str | None:
        return " > ".join(h[1] for h in heading_stack) if heading_stack else None

    def flush():
        nonlocal current
        if current and current.paragraphs:
            sections.append(current)
        current = None

    for el in elements:
        if el.type == "heading":
            flush()
            level = el.level or 1
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, el.text))
            continue

        if current is None:
            current = _Section(heading_path=heading_path(), paragraphs=[], page_start=el.page, page_end=el.page)
        current.paragraphs.append(el.text)
        if el.page is not None:
            current.page_end = el.page
            if current.page_start is None:
                current.page_start = el.page

    flush()
    return sections


def chunk_elements(
    elements: list[Element],
    target_tokens: int = None,
    overlap_tokens: int = None,
) -> list[ChunkDraft]:
    target_tokens = target_tokens or settings.chunk_target_tokens
    overlap_tokens = overlap_tokens or settings.chunk_overlap_tokens

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=target_tokens * _CHARS_PER_TOKEN,
        chunk_overlap=overlap_tokens * _CHARS_PER_TOKEN,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[ChunkDraft] = []
    for section in _group_into_sections(elements):
        section_text = "\n\n".join(section.paragraphs)
        for piece in splitter.split_text(section_text):
            chunks.append(ChunkDraft(
                text=piece,
                heading_path=section.heading_path,
                page_start=section.page_start,
                page_end=section.page_end,
                token_count=max(1, len(piece) // _CHARS_PER_TOKEN),
            ))
    return chunks
