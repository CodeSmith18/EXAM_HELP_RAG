from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from app import database
from app.config import get_settings


def get_embeddings() -> HuggingFaceEmbeddings:
    settings = get_settings()
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def vector_index_exists(path: Path) -> bool:
    return (path / "index.faiss").exists() and (path / "index.pkl").exists()


def load_vector_store() -> FAISS | None:
    settings = get_settings()
    if not vector_index_exists(settings.vector_path):
        return None
    return FAISS.load_local(
        str(settings.vector_path),
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def rebuild_vector_store() -> None:
    settings = get_settings()
    chunks = database.list_chunks()
    if settings.vector_path.exists():
        shutil.rmtree(settings.vector_path)
    settings.vector_path.mkdir(parents=True, exist_ok=True)
    if not chunks:
        return

    docs = [
        Document(
            page_content=chunk["text"],
            metadata={
                **chunk["metadata"],
                "chunk_id": chunk["id"],
                "document_id": chunk["document_id"],
                "page_number": chunk["page_number"],
            },
        )
        for chunk in chunks
    ]
    store = FAISS.from_documents(docs, get_embeddings(), ids=[chunk["id"] for chunk in chunks])
    store.save_local(str(settings.vector_path))


def build_chunks_from_pages(
    *,
    document_id: str,
    file_name: str,
    pages: list[dict[str, str | int]],
) -> list[dict[str, Any]]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[dict[str, Any]] = []
    chunk_index = 0
    for page in pages:
        text = str(page["text"]).strip()
        if not text:
            continue
        page_number = int(page["page_number"])
        for piece in splitter.split_text(text):
            chunk_id = str(uuid.uuid4())
            chunks.append(
                {
                    "id": chunk_id,
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "text": piece,
                    "metadata": {
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "file_name": file_name,
                        "page_number": page_number,
                        "chunk_index": chunk_index,
                    },
                }
            )
            chunk_index += 1
    return chunks


def similarity_search(query: str, *, k: int, document_ids: list[str] | None = None) -> list[tuple[Document, float]]:
    store = load_vector_store()
    if store is None:
        return []
    allowed_ids = {document_id for document_id in (document_ids or []) if document_id}
    metadata_filter = None
    if allowed_ids:
        metadata_filter = lambda metadata: str(metadata.get("document_id", "")) in allowed_ids
    return store.similarity_search_with_score(
        query,
        k=k,
        filter=metadata_filter,
        fetch_k=max(20, k * 10),
    )
