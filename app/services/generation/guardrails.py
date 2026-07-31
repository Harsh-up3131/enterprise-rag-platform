"""
Guardrails: lightweight input/output checks.

POC scope: a small set of deterministic checks proving the *placement* of
guardrails in the pipeline (before retrieval, after generation) rather than
a comprehensive safety system. Production hardening (blueprint §OWASP
reference) should add: dedicated prompt-injection classifiers, PII
detection/redaction, and adversarial-document test suites.
"""
import re
import unicodedata

_INJECTION_PATTERNS = [
    re.compile(r"ignore (all|any|previous) instructions", re.I),
    re.compile(r"disregard (the|your) system prompt", re.I),
    re.compile(r"reveal (the|your) system prompt", re.I),
]


def sanitize_text(text: str) -> str:
    """Normalize user text by removing control characters and collapsing whitespace."""
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(ch for ch in normalized if ch.isprintable() or ch in "\n\t")
    normalized = normalized.replace("\u200b", "")
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"[\x00-\x1f\x7f]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def check_input(question: str) -> tuple[bool, str | None]:
    """Returns (is_allowed, rejection_reason)."""
    if not question or not question.strip():
        return False, "Empty question."

    sanitized_question = sanitize_text(question)
    if not sanitized_question:
        return False, "Empty question."

    if len(sanitized_question) > 4000:
        return False, "Question too long."

    if any(pattern.search(sanitized_question) for pattern in _INJECTION_PATTERNS):
        return False, "Question contains disallowed prompt-injection content."

    return True, None


def flag_suspicious_evidence(chunk_text: str) -> bool:
    """
    Flags evidence text that looks like it's trying to instruct the model
    (indirect prompt injection via document content, per blueprint's
    'retrieved documents are untrusted input' rule). The prompt template
    already tells the model to ignore in-evidence instructions; this is a
    belt-and-suspenders signal surfaced in the trace for review.
    """
    return any(p.search(chunk_text) for p in _INJECTION_PATTERNS)


def check_output(answer_text: str) -> tuple[bool, str | None]:
    """Basic output check — extend with PII/toxicity checks in production."""
    if not answer_text or not answer_text.strip():
        return False, "Empty generation."
    return True, None
