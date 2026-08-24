"""Load ParcelPilot PDF documents and extract text."""

import re
from pathlib import Path

from pypdf import PdfReader

from app.retrieval.models import ExtractedDocument

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"

HEADER_KEYS = (
    "Status",
    "Effective",
    "Updated",
    "Supersedes",
    "Superseded by",
    "Account",
    "Customer",
    "Plan",
    "Term",
)


def normalize_pdf_text(raw: str) -> str:
    """Rebuild readable text from word-per-line PDF extraction."""
    tokens = [line.strip() for line in raw.splitlines() if line.strip()]
    text = re.sub(r"\s+", " ", " ".join(tokens)).strip()
    for key in HEADER_KEYS:
        text = re.sub(rf"\s+({re.escape(key)}:)", r"\n\1", text)
    text = re.sub(r"\s+(\d+\.\s+[A-Z])", r"\n\1", text)
    text = re.sub(r"\s+(KI-\d+\s+-)", r"\n\1", text)
    text = re.sub(r"\s+●\s+", "\n● ", text)
    return text.strip()


def _parse_title(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def _parse_header_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        for key in HEADER_KEYS:
            prefix = f"{key}:"
            if stripped.startswith(prefix) and key not in metadata:
                value = stripped[len(prefix) :].strip()
                if value:
                    metadata[key] = value
    return metadata


def load_pdf(path: Path) -> ExtractedDocument:
    reader = PdfReader(str(path))
    pages = [normalize_pdf_text(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(page for page in pages if page).strip()
    return ExtractedDocument(
        source_filename=path.name,
        title=_parse_title(text),
        text=text,
        page_count=len(reader.pages),
        metadata=_parse_header_metadata(text),
    )


def load_documents(documents_dir: Path | None = None) -> list[ExtractedDocument]:
    directory = Path(documents_dir) if documents_dir else DEFAULT_DOCUMENTS_DIR
    pdf_paths = sorted(directory.glob("*.pdf"))
    return [load_pdf(path) for path in pdf_paths]
