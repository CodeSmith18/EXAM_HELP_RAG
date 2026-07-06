from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    vector_db_path: str = "backend/data/vector_store"
    database_url: str = "sqlite:///backend/data/examprep.sqlite3"
    upload_dir: str = "backend/data/uploads"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 900
    chunk_overlap: int = 125
    retrieval_k: int = 6
    max_upload_mb: int = 25
    max_upload_files: int = 5
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            return resolve_project_path(self.database_url.replace("sqlite:///", "", 1))
        return resolve_project_path(self.database_url)

    @property
    def vector_path(self) -> Path:
        return resolve_project_path(self.vector_db_path)

    @property
    def upload_path(self) -> Path:
        return resolve_project_path(self.upload_dir)

    @property
    def cors_origins(self) -> list[str]:
        origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
        for raw_origin in self.frontend_origin.split(","):
            origin = raw_origin.strip()
            if not origin:
                continue
            if not origin.startswith(("http://", "https://")):
                origin = f"https://{origin}"
            origins.append(origin.rstrip("/"))
        return list(dict.fromkeys(origins))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.vector_path.mkdir(parents=True, exist_ok=True)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    return settings
