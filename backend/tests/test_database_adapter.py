from __future__ import annotations


def test_postgres_adapter_translates_sqlite_placeholders() -> None:
    from app.database import DatabaseConnection

    connection = DatabaseConnection(raw_connection=object(), dialect="postgres")

    assert connection._prepare_sql("SELECT * FROM users WHERE id = ? AND email = ?") == (
        "SELECT * FROM users WHERE id = %s AND email = %s"
    )


def test_postgres_url_normalization() -> None:
    from app.database import normalize_postgres_url

    assert normalize_postgres_url("postgres://user:pass@localhost/db") == "postgresql://user:pass@localhost/db"
    assert normalize_postgres_url("postgresql+psycopg2://user:pass@localhost/db") == "postgresql://user:pass@localhost/db"
