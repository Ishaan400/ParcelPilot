from app.retrieval.chunker import chunk_document, chunk_documents
from app.retrieval.loader import DEFAULT_DOCUMENTS_DIR, load_documents, load_pdf
from app.retrieval.retriever import DocumentRetriever

EXPECTED_PDFS = [
    "01_Support_Policy_v3_CURRENT.pdf",
    "02_Support_Policy_v2_DEPRECATED.pdf",
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
    "04_Product_Operations_Guide_and_Known_Issues.pdf",
    "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    "06_LumenWorks_Service_Agreement.pdf",
]


def test_loads_six_pdfs() -> None:
    documents = load_documents()
    assert [document.source_filename for document in documents] == EXPECTED_PDFS
    assert all(document.text.strip() for document in documents)
    assert all(document.page_count >= 1 for document in documents)


def test_extracted_text_preserves_filename_and_header_metadata() -> None:
    documents = {document.source_filename: document for document in load_documents()}

    current_policy = documents["01_Support_Policy_v3_CURRENT.pdf"]
    assert "Support Policy v3" in current_policy.title
    assert current_policy.metadata["Status"] == "CURRENT"
    assert "first-response" in current_policy.text

    northstar = documents["05_Northstar_Logistics_Enterprise_Agreement.pdf"]
    assert northstar.metadata["Account"] == "ACCT-001"
    assert northstar.metadata["Customer"] == "Northstar Logistics"


def test_load_pdf_uses_source_filename() -> None:
    path = DEFAULT_DOCUMENTS_DIR / "03_Cancellation_and_Service_Credit_SOP_v4.pdf"
    document = load_pdf(path)
    assert document.source_filename == path.name
    assert "cancellation" in document.text.casefold()


def test_chunking_keeps_source_filename() -> None:
    documents = load_documents()
    chunks = chunk_documents(documents)
    assert chunks
    assert {chunk.source_filename for chunk in chunks} == set(EXPECTED_PDFS)
    assert all(chunk.text.strip() for chunk in chunks)
    assert all(chunk.chunk_id == f"{chunk.source_filename}:{chunk.chunk_index}" for chunk in chunks)


def test_section_chunking_splits_policy_sections() -> None:
    documents = {document.source_filename: document for document in load_documents()}
    chunks = chunk_document(documents["01_Support_Policy_v3_CURRENT.pdf"])
    joined = "\n".join(chunk.text for chunk in chunks)
    assert "Scope and source precedence" in joined
    assert "Severity definitions" in joined
    assert len(chunks) >= 2


def test_search_returns_source_filename_and_text() -> None:
    retriever = DocumentRetriever()
    results = retriever.search("Northstar cancellation fee")
    assert results
    top = results[0]
    assert top.source_filename == "05_Northstar_Logistics_Enterprise_Agreement.pdf"
    assert top.text.strip()
    assert top.chunk_id.startswith(top.source_filename)
    assert top.metadata.get("Account") == "ACCT-001"


def test_search_prefers_current_policy_for_response_targets() -> None:
    retriever = DocumentRetriever()
    results = retriever.search("P1 first-response targets Enterprise")
    assert results
    filenames = [result.source_filename for result in results]
    assert "01_Support_Policy_v3_CURRENT.pdf" in filenames


def test_search_finds_known_issue() -> None:
    retriever = DocumentRetriever()
    results = retriever.search("KI-208 bulk upload CSV")
    assert results
    assert results[0].source_filename == "04_Product_Operations_Guide_and_Known_Issues.pdf"
    assert "KI-208" in results[0].text


def test_empty_query_returns_no_results() -> None:
    retriever = DocumentRetriever()
    assert retriever.search("   ") == []


def test_retriever_still_indexes_deprecated_policy_for_audit() -> None:
    assert (DEFAULT_DOCUMENTS_DIR / "02_Support_Policy_v2_DEPRECATED.pdf").is_file()
    retriever = DocumentRetriever()
    hits = retriever.search("DEPRECATED Support Policy v2")
    assert any("DEPRECATED" in hit.source_filename for hit in hits)
