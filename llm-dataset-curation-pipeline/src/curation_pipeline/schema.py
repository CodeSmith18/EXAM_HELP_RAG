from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

PIPELINE_VERSION = "0.1.0"


class RawPage(BaseModel):
    url: str
    final_url: str
    status_code: int
    fetched_at: str
    content_type: str | None = None
    html: str = ""
    depth: int = 0
    error: str | None = None


class CuratedRecord(BaseModel):
    id: str
    source_url: str
    domain: str
    title: str
    text: str
    language: str
    language_confidence: float
    license: str
    source_type: str
    fetched_at: str
    processed_at: str
    content_hash: str
    word_count: int
    char_count: int
    quality_flags: list[str] = Field(default_factory=list)
    pipeline_version: str = PIPELINE_VERSION


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return "local_file"
    return parsed.netloc.lower()


def record_to_jsonable(record: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(record, BaseModel):
        return record.model_dump(mode="json")
    return record

