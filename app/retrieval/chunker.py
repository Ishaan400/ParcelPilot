"""Split extracted PDF text into retrieval chunks."""

import re

from app.retrieval.models import DocumentChunk, ExtractedDocument

SECTION_SPLIT = re.compile(
    r"(?=^\d+\.\s+[A-Z]|^KI-\d+\s+-)",
    re.MULTILINE,
)


def chunk_document(document: ExtractedDocument) -> list[DocumentChunk]:
    parts = [part.strip() for part in SECTION_SPLIT.split(document.text) if part.strip()]
    if not parts:
        parts = [document.text.strip()] if document.text.strip() else []

    chunks: list[DocumentChunk] = []
    for index, text in enumerate(parts):
        chunks.append(
            DocumentChunk(
                chunk_id=f"{document.source_filename}:{index}",
                source_filename=document.source_filename,
                title=document.title,
                page_count=document.page_count,
                chunk_index=index,
                text=text,
                metadata=dict(document.metadata),
            )
        )
    return chunks


def chunk_documents(documents: list[ExtractedDocument]) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for document in documents:
        chunks.extend(chunk_document(document))
    return chunks
