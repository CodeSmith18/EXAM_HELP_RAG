from __future__ import annotations


def test_postgres_adapter_translates_sqlite_placeholders() -> None:
    from app.database import DatabaseConnection

    connection = DatabaseConnection(raw_connection=object(), dialect="postgres")

    assert connection._prepare_sql("SELECT * FROM users WHERE id = ? AND email = ?") == (
        "SELECT * FROM users WHERE id = %s AND email = %s"
    )


def test_generated_test_upsert_sql_is_postgres_compatible() -> None:
    from app.database import DatabaseConnection, generated_test_upsert_sql

    connection = DatabaseConnection(raw_connection=object(), dialect="postgres")
    prepared_sql = connection._prepare_sql(generated_test_upsert_sql())

    assert "INSERT OR REPLACE" not in prepared_sql
    assert "ON CONFLICT (id) DO UPDATE" in prepared_sql
    assert "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)" in prepared_sql


def test_postgres_url_normalization() -> None:
    from app.database import normalize_postgres_url

    assert normalize_postgres_url("postgres://user:pass@localhost/db") == "postgresql://user:pass@localhost/db"
    assert normalize_postgres_url("postgresql+psycopg2://user:pass@localhost/db") == "postgresql://user:pass@localhost/db"
