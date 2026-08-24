"""Document and chunk schemas for PDF retrieval."""

from pydantic import BaseModel, Field


class ExtractedDocument(BaseModel):
    source_filename: str
    title: str
    text: str
    page_count: int
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    chunk_id: str
    source_filename: str
    title: str
    page_count: int
    chunk_index: int
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    text: str
    source_filename: str
    title: str
    chunk_id: str
    chunk_index: int
    score: float
    metadata: dict[str, str] = Field(default_factory=dict)
