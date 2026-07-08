from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class PipelineConfig(BaseModel):
    project_name: str = "llm_dataset_curation_demo"
    allowed_domains: list[str] = Field(default_factory=list)
    seed_urls: list[str]
    max_pages: int = 30
    max_depth: int = 1
    request_delay_seconds: float = 1.0
    language_allowlist: list[str] = Field(default_factory=lambda: ["en"])
    language_min_confidence: float = 0.70
    license: str = "unknown"
    source_type: str = "public_web"
    min_words: int = 80
    min_chars: int = 500
    near_duplicate_threshold: float = 0.85
    shingle_size: int = 5
    user_agent: str = "LLMDatasetCurationPipeline/0.1 (+portfolio project)"

    @field_validator("allowed_domains", "language_allowlist", mode="before")
    @classmethod
    def normalize_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item) for item in value]

    @field_validator("max_pages", "max_depth", "min_words", "min_chars")
    @classmethod
    def non_negative_ints(cls, value: int) -> int:
        if value < 0:
            raise ValueError("value must be non-negative")
        return value


def load_config(path: str | Path) -> PipelineConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return PipelineConfig(**payload)

