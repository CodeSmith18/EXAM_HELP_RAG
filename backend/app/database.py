from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

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


class QueryResult:
    def __init__(self, cursor: Any) -> None:
        self.cursor = cursor

    def fetchone(self) -> Any:
        return self.cursor.fetchone()

    def fetchall(self) -> list[Any]:
        return list(self.cursor.fetchall())


class DatabaseConnection:
    def __init__(self, raw_connection: Any, dialect: str) -> None:
        self.raw_connection = raw_connection
        self.dialect = dialect

    def execute(self, sql: str, params: Sequence[Any] = ()) -> QueryResult:
        cursor = self.raw_connection.cursor()
        cursor.execute(self._prepare_sql(sql), tuple(params))
        return QueryResult(cursor)

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> QueryResult:
        cursor = self.raw_connection.cursor()
        cursor.executemany(self._prepare_sql(sql), [tuple(item) for item in params])
        return QueryResult(cursor)

    def commit(self) -> None:
        self.raw_connection.commit()

    def close(self) -> None:
        self.raw_connection.close()

    def _prepare_sql(self, sql: str) -> str:
        if self.dialect == "postgres":
            return sql.replace("?", "%s")
        return sql


def normalize_postgres_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return database_url


def open_database_connection() -> DatabaseConnection:
    settings = get_settings()
    if settings.is_postgres:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as exc:
            raise RuntimeError("Install psycopg2-binary to use a PostgreSQL DATABASE_URL.") from exc

        raw = psycopg2.connect(normalize_postgres_url(settings.database_url), cursor_factory=RealDictCursor)
        return DatabaseConnection(raw, "postgres")

    raw = sqlite3.connect(settings.database_path)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return DatabaseConnection(raw, "sqlite")


@contextmanager
def get_connection():
    conn = open_database_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                owner_id TEXT,
                file_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'uploaded',
                error TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
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
                owner_id TEXT,
                mode TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                topic TEXT,
                document_ids_json TEXT NOT NULL,
                questions_json TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_generated_tests_created_at ON generated_tests(created_at)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                owner_id TEXT,
                submitted_at TEXT NOT NULL,
                mcq_json TEXT,
                written_json TEXT,
                percentage REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (test_id) REFERENCES generated_tests(id) ON DELETE CASCADE,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_submitted_at ON test_results(submitted_at)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS study_sessions (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                include_diagram INTEGER NOT NULL,
                document_ids_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_study_sessions_owner_id ON study_sessions(owner_id)")
        ensure_column(conn, "documents", "owner_id", "TEXT")
        ensure_column(conn, "generated_tests", "owner_id", "TEXT")
        ensure_column(conn, "test_results", "owner_id", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_owner_id ON documents(owner_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_generated_tests_owner_id ON generated_tests(owner_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_owner_id ON test_results(owner_id)")


def ensure_column(conn: DatabaseConnection, table_name: str, column_name: str, column_type: str) -> None:
    if conn.dialect == "postgres":
        row = conn.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = ? AND column_name = ?
            """,
            (table_name, column_name),
        ).fetchone()
        if not row:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        return

    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def create_user(*, email: str, password_hash: str, full_name: str | None = None) -> dict[str, Any]:
    user_id = uuid.uuid4().hex
    created_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, full_name, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, email.strip().lower(), password_hash, full_name, created_at),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return row_to_dict(row) or {}


def get_user(user_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return row_to_dict(row)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
        return row_to_dict(row)


def create_document(document_id: str, file_name: str, stored_path: Path, owner_id: str | None = None) -> dict[str, Any]:
    uploaded_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO documents (id, owner_id, file_name, stored_path, uploaded_at, status)
            VALUES (?, ?, ?, ?, ?, 'uploaded')
            """,
            (document_id, owner_id, file_name, str(stored_path), uploaded_at),
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


def list_documents(owner_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if owner_id:
            rows = conn.execute(
                "SELECT * FROM documents WHERE owner_id = ? ORDER BY uploaded_at DESC",
                (owner_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
        return [dict(row) for row in rows]


def get_document(document_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        if owner_id:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ? AND owner_id = ?",
                (document_id, owner_id),
            ).fetchone()
        else:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return row_to_dict(row)


def delete_document(document_id: str, owner_id: str) -> dict[str, Any] | None:
    document = get_document(document_id, owner_id=owner_id)
    if not document:
        return None
    with get_connection() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM documents WHERE id = ? AND owner_id = ?", (document_id, owner_id))
    return document


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


def list_chunks(document_id: str | None = None, owner_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if document_id and owner_id:
            rows = conn.execute(
                """
                SELECT chunks.* FROM chunks
                JOIN documents ON documents.id = chunks.document_id
                WHERE chunks.document_id = ? AND documents.owner_id = ?
                ORDER BY chunks.chunk_index ASC
                """,
                (document_id, owner_id),
            ).fetchall()
        elif document_id:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC",
                (document_id,),
            ).fetchall()
        elif owner_id:
            rows = conn.execute(
                """
                SELECT chunks.* FROM chunks
                JOIN documents ON documents.id = chunks.document_id
                WHERE documents.owner_id = ?
                ORDER BY chunks.created_at ASC
                """,
                (owner_id,),
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
    owner_id: str | None = None,
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
    chunks = list_chunks(owner_id=owner_id)
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


def generated_test_upsert_sql() -> str:
    return """
            INSERT INTO generated_tests
                (id, owner_id, mode, difficulty, topic, document_ids_json, questions_json, sources_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                owner_id = excluded.owner_id,
                mode = excluded.mode,
                difficulty = excluded.difficulty,
                topic = excluded.topic,
                document_ids_json = excluded.document_ids_json,
                questions_json = excluded.questions_json,
                sources_json = excluded.sources_json,
                created_at = excluded.created_at
            """


def save_generated_test(
    *,
    test_id: str,
    owner_id: str | None,
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
            generated_test_upsert_sql(),
            (
                test_id,
                owner_id,
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


def get_generated_test(test_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        if owner_id:
            row = conn.execute(
                "SELECT * FROM generated_tests WHERE id = ? AND owner_id = ?",
                (test_id, owner_id),
            ).fetchone()
        else:
            row = conn.execute("SELECT * FROM generated_tests WHERE id = ?", (test_id,)).fetchone()
        return generated_test_row_to_dict(row)


def list_generated_tests(limit: int = 25, owner_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if owner_id:
            rows = conn.execute(
                "SELECT * FROM generated_tests WHERE owner_id = ? ORDER BY created_at DESC LIMIT ?",
                (owner_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM generated_tests ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [item for row in rows if (item := generated_test_row_to_dict(row))]


def create_test_result(
    *,
    test_id: str,
    owner_id: str | None,
    mcq: dict[str, Any] | None,
    written: dict[str, Any] | None,
    percentage: float,
) -> dict[str, Any]:
    result_id = uuid.uuid4().hex
    submitted_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO test_results (id, test_id, owner_id, submitted_at, mcq_json, written_json, percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                test_id,
                owner_id,
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


def list_test_results(limit: int = 25, owner_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if owner_id:
            rows = conn.execute(
                "SELECT * FROM test_results WHERE owner_id = ? ORDER BY submitted_at DESC LIMIT ?",
                (owner_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM test_results ORDER BY submitted_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [item for row in rows if (item := test_result_row_to_dict(row))]


def create_study_session(
    *,
    owner_id: str,
    topic: str,
    include_diagram: bool,
    document_ids: list[str],
    response: dict[str, Any],
) -> dict[str, Any]:
    session_id = uuid.uuid4().hex
    created_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO study_sessions
                (id, owner_id, topic, include_diagram, document_ids_json, response_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                owner_id,
                topic,
                1 if include_diagram else 0,
                json.dumps(document_ids),
                json.dumps(response),
                created_at,
            ),
        )
        row = conn.execute("SELECT * FROM study_sessions WHERE id = ?", (session_id,)).fetchone()
        return study_session_row_to_dict(row) or {}


def study_session_row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["include_diagram"] = bool(item["include_diagram"])
    item["document_ids"] = json.loads(item.pop("document_ids_json"))
    item["response"] = json.loads(item.pop("response_json"))
    return item


def list_study_sessions(owner_id: str, limit: int = 25) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM study_sessions WHERE owner_id = ? ORDER BY created_at DESC LIMIT ?",
            (owner_id, limit),
        ).fetchall()
        return [item for row in rows if (item := study_session_row_to_dict(row))]


def get_study_session(session_id: str, owner_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM study_sessions WHERE id = ? AND owner_id = ?",
            (session_id, owner_id),
        ).fetchone()
        return study_session_row_to_dict(row)


def delete_study_session(session_id: str, owner_id: str) -> bool:
    if not get_study_session(session_id, owner_id):
        return False
    with get_connection() as conn:
        conn.execute("DELETE FROM study_sessions WHERE id = ? AND owner_id = ?", (session_id, owner_id))
    return True
