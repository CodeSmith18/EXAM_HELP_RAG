from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile

from app import database
from app.config import get_settings
from app.models import SourceRef
from app.prompts import GENERAL_QA_PROMPT, STUDY_MODE_PROMPT
from app.services.groq_client import GroqClient
from app.services.pdf_loader import extract_pdf_pages
from app.services.vector_store import build_chunks_from_pages, rebuild_vector_store, similarity_search


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


def retrieve_context(
    query: str,
    *,
    k: int | None = None,
    document_ids: list[str] | None = None,
) -> tuple[str, list[SourceRef]]:
    settings = get_settings()
    results = similarity_search(query, k=k or settings.retrieval_k, document_ids=document_ids)
    return format_context(results)


async def save_upload(file: UploadFile) -> tuple[str, Path]:
    settings = get_settings()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{file.filename or 'File'} is not a PDF.")

    safe_name = Path(file.filename).name.replace("/", "_")
    document_id = __import__("uuid").uuid4().hex
    stored_path = settings.upload_path / f"{document_id}_{safe_name}"
    with stored_path.open("wb") as output:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    database.create_document(document_id, safe_name, stored_path)
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
) -> tuple[str, list[SourceRef]]:
    context, sources = retrieve_context(question, k=top_k, document_ids=document_ids)
    if not context:
        return "The answer was not found in the uploaded PDF.", []
    payload = await GroqClient().chat_json(
        GENERAL_QA_PROMPT.format(question=question, context=context),
        temperature=0.1,
    )
    return str(payload.get("answer", "The answer was not found in the uploaded PDF.")), sources


async def study_topic(topic: str, include_diagram: bool, document_ids: list[str] | None = None) -> dict:
    context, sources = retrieve_context(topic, document_ids=document_ids)
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
    )
    if not include_diagram:
        payload["mermaid_diagram"] = None
    payload["topic"] = topic
    payload["sources"] = sources
    return payload
