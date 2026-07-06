from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document


def test_semantic_search_runs_before_fallback_chunks(temp_app_settings: Path, monkeypatch) -> None:
    from app import database
    from app.services import rag

    database.create_document("doc-1", "notes.pdf", temp_app_settings / "notes.pdf")
    database.update_document("doc-1", status="ready", page_count=1, chunk_count=2)
    database.replace_chunks(
        "doc-1",
        [
            {
                "id": "first-chunk",
                "chunk_index": 0,
                "page_number": 1,
                "text": "This is only introductory filler text.",
                "metadata": {"file_name": "notes.pdf", "document_id": "doc-1", "page_number": 1},
            },
            {
                "id": "second-chunk",
                "chunk_index": 1,
                "page_number": 1,
                "text": "More filler text that should not win retrieval.",
                "metadata": {"file_name": "notes.pdf", "document_id": "doc-1", "page_number": 1},
            },
        ],
    )

    def fake_similarity_search(query: str, *, k: int, document_ids: list[str] | None = None):
        return [
            (
                Document(
                    page_content="Semantic target content about photosynthesis.",
                    metadata={
                        "chunk_id": "semantic-chunk",
                        "document_id": "doc-1",
                        "file_name": "notes.pdf",
                        "page_number": 1,
                    },
                ),
                0.1,
            )
        ]

    monkeypatch.setattr(rag, "similarity_search", fake_similarity_search)

    context, sources = rag.retrieve_context("photosynthesis", k=1, document_ids=["doc-1"])

    assert "Semantic target content" in context
    assert sources[0].chunk_id == "semantic-chunk"
