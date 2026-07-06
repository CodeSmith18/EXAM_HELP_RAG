from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from langchain_core.documents import Document

from app import database
from app.config import get_settings
from app.models import LLMAnswerPayload, LLMStudyModePayload, SourceRef
from app.prompts import GENERAL_QA_PROMPT, STUDY_MODE_PROMPT
from app.services.groq_client import GroqClient
from app.services.pdf_loader import extract_pdf_pages
from app.services.vector_store import build_chunks_from_pages, rebuild_vector_store, similarity_search


DISTINCTIVE_STOP_WORDS = {
    "about",
    "after",
    "also",
    "are",
    "can",
    "does",
    "explain",
    "from",
    "have",
    "into",
    "that",
    "tell",
    "the",
    "this",
    "what",
    "when",
    "where",
    "with",
    "your",
}

ALLOWED_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
    "binary/octet-stream",
}
PDF_SIGNATURE = b"%PDF-"


def source_from_metadata(metadata: dict, score: float | None = None) -> SourceRef:
    return SourceRef(
        document_id=str(metadata.get("document_id", "")),
        file_name=str(metadata.get("file_name", "Unknown PDF")),
        page_number=int(metadata.get("page_number", 0)),
        chunk_id=str(metadata.get("chunk_id", "")),
        score=float(score) if score is not None else None,
    )


def dedupe_sources(sources: list[SourceRef]) -> list[SourceRef]:
    seen: set[tuple[str, int, str]] = set()
    unique: list[SourceRef] = []
    for source in sources:
        key = (source.document_id, source.page_number, source.chunk_id)
        if key not in seen:
            unique.append(source)
            seen.add(key)
    return unique


def format_context(results: list[tuple[object, float]]) -> tuple[str, list[SourceRef]]:
    parts: list[str] = []
    sources: list[SourceRef] = []
    for index, (doc, score) in enumerate(results, start=1):
        metadata = getattr(doc, "metadata", {})
        source = source_from_metadata(metadata, float(score))
        sources.append(source)
        parts.append(
            "\n".join(
                [
                    f"[Source {index}] PDF: {source.file_name}, page: {source.page_number}, chunk: {source.chunk_id}",
                    getattr(doc, "page_content", ""),
                ]
            )
        )
    return "\n\n---\n\n".join(parts), dedupe_sources(sources)


def keyword_chunks_to_results(chunks: list[dict]) -> list[tuple[Document, float]]:
    return [
        (
            Document(
                page_content=chunk["text"],
                metadata={
                    **chunk["metadata"],
                    "chunk_id": chunk["id"],
                    "document_id": chunk["document_id"],
                    "page_number": chunk["page_number"],
                },
            ),
            -float(chunk.get("keyword_score", 0)),
        )
        for chunk in chunks
    ]


def fallback_chunks_to_results(
    *,
    document_ids: list[str] | None,
    owner_id: str | None = None,
    limit: int,
) -> list[tuple[Document, float]]:
    allowed_ids = {document_id for document_id in (document_ids or []) if document_id}
    chunks = [
        chunk
        for chunk in database.list_chunks(owner_id=owner_id)
        if not allowed_ids or chunk["document_id"] in allowed_ids
    ][:limit]
    return keyword_chunks_to_results(chunks)


def merge_results(*result_groups: list[tuple[Document, float]], limit: int) -> list[tuple[Document, float]]:
    seen: set[str] = set()
    merged: list[tuple[Document, float]] = []
    for result_group in result_groups:
        for doc, score in result_group:
            chunk_id = str(doc.metadata.get("chunk_id", ""))
            fallback_key = f"{doc.metadata.get('document_id', '')}:{doc.metadata.get('page_number', '')}:{doc.page_content[:80]}"
            key = chunk_id or fallback_key
            if key in seen:
                continue
            seen.add(key)
            merged.append((doc, score))
            if len(merged) >= limit:
                return merged
    return merged


def sanitize_upload_filename(filename: str) -> str:
    safe_name = Path(filename).name.replace("\x00", "").strip()
    safe_name = re.sub(r"\s+", " ", safe_name)
    safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", safe_name)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{safe_name} is not a PDF.")
    return safe_name


def validate_upload_batch(files: list[UploadFile]) -> None:
    settings = get_settings()
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one PDF.")
    if len(files) > settings.max_upload_files:
        raise HTTPException(status_code=400, detail=f"Upload up to {settings.max_upload_files} PDFs at a time.")

    seen_names: set[str] = set()
    for file in files:
        safe_name = sanitize_upload_filename(file.filename or "")
        content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        if content_type and content_type not in ALLOWED_PDF_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail=f"{safe_name} must be uploaded as a PDF.")
        if safe_name.lower() in seen_names:
            raise HTTPException(status_code=400, detail=f"{safe_name} was selected more than once.")
        seen_names.add(safe_name.lower())

        file_size = getattr(file, "size", None)
        if file_size == 0:
            raise HTTPException(status_code=400, detail=f"{safe_name} is empty.")
        if file_size and file_size > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"{safe_name} is larger than {settings.max_upload_mb} MB.")


def ensure_pdf_chunk(chunk: bytes, filename: str) -> None:
    if PDF_SIGNATURE not in chunk[:1024]:
        raise HTTPException(status_code=400, detail=f"{filename} is not a valid PDF file.")


def validate_ready_documents(document_ids: list[str] | None, owner_id: str | None = None) -> None:
    for document_id in document_ids or []:
        document = database.get_document(document_id, owner_id=owner_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} was not found.")
        if document["status"] != "ready":
            raise HTTPException(status_code=400, detail=f"{document['file_name']} is not ready for retrieval yet.")


def resolve_retrieval_document_ids(document_ids: list[str] | None, owner_id: str | None = None) -> list[str] | None:
    explicit_ids = [document_id for document_id in (document_ids or []) if document_id]
    if explicit_ids:
        validate_ready_documents(explicit_ids, owner_id=owner_id)
        return explicit_ids
    if owner_id:
        return [document["id"] for document in database.list_documents(owner_id=owner_id) if document["status"] == "ready"]
    return None


def should_prioritize_keyword(query: str, keyword_chunks: list[dict]) -> bool:
    return has_distinctive_keyword_match(query, keyword_chunks)


def cap_result_count(results: list[tuple[Document, float]], limit: int) -> list[tuple[Document, float]]:
    return results[:limit]


def keyword_or_semantic_results(
    *,
    keyword_results: list[tuple[Document, float]],
    semantic_results: list[tuple[Document, float]],
    keyword_first: bool,
    limit: int,
) -> list[tuple[Document, float]]:
    if keyword_first:
        return merge_results(keyword_results, semantic_results, limit=limit)
    return merge_results(semantic_results, keyword_results, limit=limit)


def has_distinctive_keyword_match(query: str, chunks: list[dict]) -> bool:
    if not chunks:
        return False
    terms = [
        term
        for term in re.findall(r"[a-z0-9][a-z0-9+#.-]*", query.lower())
        if len(term) >= 5 and term not in DISTINCTIVE_STOP_WORDS
    ]
    if not terms:
        return False
    top_text = chunks[0]["text"].lower()
    return any(term in top_text for term in terms)


def retrieve_context(
    query: str,
    *,
    k: int | None = None,
    document_ids: list[str] | None = None,
    owner_id: str | None = None,
) -> tuple[str, list[SourceRef]]:
    settings = get_settings()
    retrieval_document_ids = resolve_retrieval_document_ids(document_ids, owner_id=owner_id)
    if owner_id and not retrieval_document_ids:
        return "", []
    limit = max(1, k or settings.retrieval_k)
    keyword_chunks = database.search_chunks_by_keyword(
        query,
        document_ids=retrieval_document_ids,
        owner_id=owner_id,
        limit=max(limit, 3),
    )
    keyword_results = keyword_chunks_to_results(keyword_chunks)
    try:
        semantic_results = similarity_search(query, k=limit, document_ids=retrieval_document_ids)
    except Exception:
        semantic_results = []

    results = keyword_or_semantic_results(
        keyword_results=keyword_results,
        semantic_results=semantic_results,
        keyword_first=should_prioritize_keyword(query, keyword_chunks),
        limit=limit,
    )
    if not results:
        results = cap_result_count(
            fallback_chunks_to_results(document_ids=retrieval_document_ids, owner_id=owner_id, limit=limit),
            limit,
        )
    return format_context(results)


async def save_upload(file: UploadFile, owner_id: str | None = None) -> tuple[str, Path]:
    settings = get_settings()
    safe_name = sanitize_upload_filename(file.filename or "")
    document_id = uuid.uuid4().hex
    stored_path = settings.upload_path / f"{document_id}_{safe_name}"
    max_bytes = settings.max_upload_mb * 1024 * 1024
    bytes_written = 0
    first_chunk = True

    try:
        with stored_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                if first_chunk:
                    ensure_pdf_chunk(chunk, safe_name)
                    first_chunk = False
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise HTTPException(status_code=400, detail=f"{safe_name} is larger than {settings.max_upload_mb} MB.")
                output.write(chunk)
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise

    if bytes_written == 0:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"{safe_name} is empty.")

    database.create_document(document_id, safe_name, stored_path, owner_id=owner_id)
    return document_id, stored_path


def ingest_document(document_id: str) -> dict:
    document = database.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    database.update_document(document_id, status="processing", error="")
    try:
        pages = extract_pdf_pages(Path(document["stored_path"]))
        chunks = build_chunks_from_pages(
            document_id=document_id,
            file_name=document["file_name"],
            pages=pages,
        )
        if not chunks:
            raise ValueError("No selectable text was found in this PDF.")
        database.replace_chunks(document_id, chunks)
        database.update_document(
            document_id,
            page_count=len(pages),
            chunk_count=len(chunks),
            status="ready",
            error="",
        )
        rebuild_vector_store()
    except Exception as exc:
        database.update_document(document_id, status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {exc}") from exc

    updated = database.get_document(document_id)
    return updated or document


async def ask_question(
    question: str,
    top_k: int,
    document_ids: list[str] | None = None,
    owner_id: str | None = None,
) -> tuple[str, list[SourceRef]]:
    context, sources = retrieve_context(question, k=top_k, document_ids=document_ids, owner_id=owner_id)
    if not context:
        return "The answer was not found in the uploaded PDF.", []
    payload = await GroqClient().chat_json(
        GENERAL_QA_PROMPT.format(question=question, context=context),
        temperature=0.1,
        schema_model=LLMAnswerPayload,
    )
    return str(payload.get("answer", "The answer was not found in the uploaded PDF.")), sources


async def study_topic(
    topic: str,
    include_diagram: bool,
    document_ids: list[str] | None = None,
    owner_id: str | None = None,
) -> dict:
    context, sources = retrieve_context(topic, document_ids=document_ids, owner_id=owner_id)
    if not context:
        return {
            "topic": topic,
            "simple_explanation": "This topic was not found in the uploaded PDF.",
            "key_points": [],
            "example": None,
            "important_terms": [],
            "quick_revision_summary": "Not found in the uploaded PDF.",
            "mermaid_diagram": None,
            "sources": [],
        }
    payload = await GroqClient().chat_json(
        STUDY_MODE_PROMPT.format(topic=topic, context=context),
        temperature=0.2,
        schema_model=LLMStudyModePayload,
    )
    if not include_diagram:
        payload["mermaid_diagram"] = None
    payload["topic"] = topic
    payload["sources"] = sources
    return payload
