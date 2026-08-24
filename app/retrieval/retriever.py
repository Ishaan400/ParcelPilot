"""Deterministic keyword search over PDF chunks."""

import re
from pathlib import Path

from app.retrieval.chunker import chunk_documents
from app.retrieval.loader import DEFAULT_DOCUMENTS_DIR, load_documents
from app.retrieval.models import DocumentChunk, RetrievalResult

TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_RE.finditer(text)]


def _score(query_tokens: list[str], chunk: DocumentChunk) -> float:
    if not query_tokens:
        return 0.0
    haystack = _tokens(
        f"{chunk.source_filename} {chunk.title} {chunk.text} "
        f"{' '.join(chunk.metadata.values())}"
    )
    if not haystack:
        return 0.0
    counts = {token: 0 for token in query_tokens}
    for token in haystack:
        if token in counts:
            counts[token] += 1
    matched = sum(1 for token in query_tokens if counts[token] > 0)
    if matched == 0:
        return 0.0
    frequency = sum(counts.values())
    return float(matched * 10 + frequency)


class DocumentRetriever:
    """Load, chunk, and search ParcelPilot policy PDFs."""

    def __init__(self, documents_dir: Path | None = None) -> None:
        self.documents_dir = Path(documents_dir) if documents_dir else DEFAULT_DOCUMENTS_DIR
        self.documents = load_documents(self.documents_dir)
        self.chunks = chunk_documents(self.documents)

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        query_tokens = _tokens(query)
        if not query_tokens or top_k <= 0:
            return []

        scored: list[tuple[float, DocumentChunk]] = []
        for chunk in self.chunks:
            score = _score(query_tokens, chunk)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: (-item[0], item[1].source_filename, item[1].chunk_index))
        results: list[RetrievalResult] = []
        for score, chunk in scored[:top_k]:
            results.append(
                RetrievalResult(
                    text=chunk.text,
                    source_filename=chunk.source_filename,
                    title=chunk.title,
                    chunk_id=chunk.chunk_id,
                    chunk_index=chunk.chunk_index,
                    score=score,
                    metadata=dict(chunk.metadata),
                )
            )
        return results
