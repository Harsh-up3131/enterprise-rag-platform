from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """One question to grade. `relevant_chunk_ids` is optional ground truth —
    supply it to get a real recall@k, omit it and the case is excluded from
    the recall average rather than scored as a trivial 1.0."""
    question: str = Field(min_length=1)
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    expect_abstain: bool = False
    tags: list[str] = Field(default_factory=list)


class EvalRunRequest(BaseModel):
    """Omit `cases` to fall back to the bundled sample eval set."""
    cases: list[EvalCase] | None = None
    # When true, cases missing `relevant_chunk_ids` are counted as recall=0.0
    # instead of being excluded from the aggregate (prevents "n/a").
    score_missing_recall_as_zero: bool = False
