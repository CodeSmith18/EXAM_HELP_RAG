from __future__ import annotations

import sys
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def temp_app_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    from app.config import get_settings

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.sqlite3'}")
    monkeypatch.setenv("VECTOR_DB_PATH", str(tmp_path / "vector_store"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("MAX_UPLOAD_FILES", "3")
    get_settings.cache_clear()

    from app import database

    database.init_db()
    yield tmp_path
    get_settings.cache_clear()
