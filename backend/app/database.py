from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.config import get_settings


STOP_WORDS = {
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
    "is",
    "tell",
    "that",
    "the",
    "this",
    "what",
    "when",
    "where",
    "with",
    "your",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection():
    db_path = get_settings().database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'uploaded',
                error TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_tests (
                id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                topic TEXT,
                document_ids_json TEXT NOT NULL,
                questions_json TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_generated_tests_created_at ON generated_tests(created_at)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                mcq_json TEXT,
                written_json TEXT,
                percentage REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (test_id) REFERENCES generated_tests(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_submitted_at ON test_results(submitted_at)")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def create_document(document_id: str, file_name: str, stored_path: Path) -> dict[str, Any]:
    uploaded_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO documents (id, file_name, stored_path, uploaded_at, status)
            VALUES (?, ?, ?, ?, 'uploaded')
            """,
            (document_id, file_name, str(stored_path), uploaded_at),
        )
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return row_to_dict(row) or {}


def update_document(
    document_id: str,
    *,
    page_count: int | None = None,
    chunk_count: int | None = None,
    status: str | None = None,
    error: str | None = None,
) -> None:
    updates: list[str] = []
    values: list[Any] = []
    if page_count is not None:
        updates.append("page_count = ?")
        values.append(page_count)
    if chunk_count is not None:
        updates.append("chunk_count = ?")
        values.append(chunk_count)
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if error is not None:
        updates.append("error = ?")
        values.append(error)
    if not updates:
        return
    values.append(document_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE documents SET {', '.join(updates)} WHERE id = ?", values)


def list_documents() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
        return [dict(row) for row in rows]


def get_document(document_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return row_to_dict(row)


def replace_chunks(document_id: str, chunks: Iterable[dict[str, Any]]) -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        conn.executemany(
            """
            INSERT INTO chunks (id, document_id, chunk_index, page_number, text, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk["id"],
                    document_id,
                    chunk["chunk_index"],
                    chunk["page_number"],
                    chunk["text"],
                    json.dumps(chunk["metadata"]),
                    now,
                )
                for chunk in chunks
            ],
        )


def list_chunks(document_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if document_id:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC",
                (document_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM chunks ORDER BY created_at ASC").fetchall()
        output: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json"))
            output.append(item)
        return output


def search_chunks_by_keyword(
    query: str,
    *,
    document_ids: list[str] | None = None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    terms = [
        term
        for term in re.findall(r"[a-z0-9][a-z0-9+#.-]*", query.lower())
        if len(term) > 1 and term not in STOP_WORDS
    ]
    phrase = query.strip().lower()
    if not terms and not phrase:
        return []

    allowed_ids = {document_id for document_id in (document_ids or []) if document_id}
    chunks = list_chunks()
    scored_chunks: list[dict[str, Any]] = []

    for chunk in chunks:
        if allowed_ids and chunk["document_id"] not in allowed_ids:
            continue
        text = chunk["text"].lower()
        score = 0
        if phrase and phrase in text:
            score += 12 + text.count(phrase) * 4
        for term in terms:
            term_count = text.count(term)
            if term_count:
                score += term_count * (3 if len(term) > 4 else 1)
        if score:
            item = dict(chunk)
            item["keyword_score"] = score
            scored_chunks.append(item)

    return sorted(scored_chunks, key=lambda item: item["keyword_score"], reverse=True)[:limit]


def save_generated_test(
    *,
    test_id: str,
    mode: str,
    difficulty: str,
    topic: str | None,
    document_ids: list[str],
    questions: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    created_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO generated_tests
                (id, mode, difficulty, topic, document_ids_json, questions_json, sources_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_id,
                mode,
                difficulty,
                topic,
                json.dumps(document_ids),
                json.dumps(questions),
                json.dumps(sources),
                created_at,
            ),
        )
        row = conn.execute("SELECT * FROM generated_tests WHERE id = ?", (test_id,)).fetchone()
        return generated_test_row_to_dict(row) or {}


def generated_test_row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["document_ids"] = json.loads(item.pop("document_ids_json"))
    item["questions"] = json.loads(item.pop("questions_json"))
    item["sources"] = json.loads(item.pop("sources_json"))
    return item


def get_generated_test(test_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM generated_tests WHERE id = ?", (test_id,)).fetchone()
        return generated_test_row_to_dict(row)


def list_generated_tests(limit: int = 25) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM generated_tests ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [item for row in rows if (item := generated_test_row_to_dict(row))]


def create_test_result(
    *,
    test_id: str,
    mcq: dict[str, Any] | None,
    written: dict[str, Any] | None,
    percentage: float,
) -> dict[str, Any]:
    result_id = uuid.uuid4().hex
    submitted_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO test_results (id, test_id, submitted_at, mcq_json, written_json, percentage)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                test_id,
                submitted_at,
                json.dumps(mcq) if mcq is not None else None,
                json.dumps(written) if written is not None else None,
                percentage,
            ),
        )
        row = conn.execute("SELECT * FROM test_results WHERE id = ?", (result_id,)).fetchone()
        return test_result_row_to_dict(row) or {}


def test_result_row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    mcq_json = item.pop("mcq_json")
    written_json = item.pop("written_json")
    item["mcq"] = json.loads(mcq_json) if mcq_json else None
    item["written"] = json.loads(written_json) if written_json else None
    return item


def list_test_results(limit: int = 25) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM test_results ORDER BY submitted_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [item for row in rows if (item := test_result_row_to_dict(row))]
