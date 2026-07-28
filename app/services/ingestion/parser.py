"""
Parsing stage: file on disk -> normalized "elements" (per blueprint §12.3).

Uses LangChain's document loaders for PDF/TXT/MD, since they handle the
page-splitting and text-cleanup edge cases better than hand-rolled code and
are the standard tool for this in the ecosystem. DOCX intentionally stays
on `python-docx` directly: LangChain's docx loader (docx2txt) flattens
paragraph styles, which would lose the heading-level info this pipeline
needs for `heading_path` — so here, the hand-rolled version is genuinely
better than the framework default.

The output is intentionally decoupled from chunking: a list of typed
elements (heading/paragraph) with page numbers where available. This lets
chunking strategies be swapped/experimented with later without re-parsing
original files.

POC scope: PDF, DOCX, TXT, MD. HTML/OCR/PPTX are TODO(prod) per blueprint §12.1.
"""
from dataclasses import dataclass

import docx
from langchain_community.document_loaders import PyPDFLoader, TextLoader

PARSER_VERSION = "v2-langchain-loaders"


@dataclass
class Element:
    type: str          # "heading" | "paragraph"
    text: str
    level: int | None = None     # heading level, if type == "heading"
    page: int | None = None      # page number, if known


def parse_document(file_path: str, source_type: str) -> list[Element]:
    if source_type == "pdf":
        return _parse_pdf(file_path)
    if source_type == "docx":
        return _parse_docx(file_path)
    if source_type in ("txt", "md"):
        return _parse_plaintext(file_path)
    raise ValueError(f"Unsupported source_type for POC parser: {source_type}")


def _parse_pdf(file_path: str) -> list[Element]:
    # PyPDFLoader returns one LangChain Document per page with page number
    # already in metadata — exactly what we need for citation page numbers.
    langchain_docs = PyPDFLoader(file_path).load()
    elements: list[Element] = []
    for doc in langchain_docs:
        page_num = doc.metadata.get("page", 0) + 1
        for para in [p.strip() for p in doc.page_content.split("\n\n") if p.strip()]:
            elements.append(Element(type="paragraph", text=para, page=page_num))
    return elements


def _parse_docx(file_path: str) -> list[Element]:
    document = docx.Document(file_path)
    elements: list[Element] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower()
        if style.startswith("heading"):
            level = int(style.replace("heading", "").strip() or 1)
            elements.append(Element(type="heading", text=text, level=level))
        else:
            elements.append(Element(type="paragraph", text=text))
    return elements


def _parse_plaintext(file_path: str) -> list[Element]:
    langchain_docs = TextLoader(file_path, encoding="utf-8").load()
    text = langchain_docs[0].page_content if langchain_docs else ""
    elements: list[Element] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Naive markdown heading detection ("# Heading") — good enough for POC.
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            elements.append(Element(type="heading", text=stripped.lstrip("#").strip(), level=level))
        else:
            elements.append(Element(type="paragraph", text=stripped))
    return elements
