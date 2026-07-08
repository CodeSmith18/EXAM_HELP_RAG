from __future__ import annotations

import re
import string
import unicodedata
from collections import Counter

from .config import PipelineConfig


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def normalize_for_hash(text: str) -> str:
    normalized = clean_text(text).lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def alphabetic_ratio(text: str) -> float:
    if not text:
        return 0.0
    alpha = sum(1 for char in text if char.isalpha())
    return alpha / len(text)


def punctuation_ratio(text: str) -> float:
    if not text:
        return 0.0
    punctuation = sum(1 for char in text if char in string.punctuation)
    return punctuation / len(text)


def repeated_line_ratio(text: str) -> float:
    lines = [line.strip().lower() for line in text.splitlines() if len(line.strip()) > 20]
    if len(lines) < 4:
        return 0.0
    counts = Counter(lines)
    repeated = sum(count for count in counts.values() if count > 1)
    return repeated / len(lines)


def quality_flags(text: str) -> list[str]:
    flags: list[str] = []
    if alphabetic_ratio(text) < 0.35:
        flags.append("low_alpha_ratio")
    if punctuation_ratio(text) > 0.25:
        flags.append("excessive_punctuation")
    if repeated_line_ratio(text) > 0.35:
        flags.append("repeated_lines")
    return flags


def clean_and_validate(record: dict, config: PipelineConfig) -> tuple[dict | None, dict | None]:
    cleaned_text = clean_text(record.get("text", ""))
    words = word_count(cleaned_text)
    chars = len(cleaned_text)

    if not cleaned_text:
        return None, {**record, "drop_reason": "empty_text"}

    flags = quality_flags(cleaned_text)
    blocking_flags = {"low_alpha_ratio", "excessive_punctuation", "repeated_lines"}
    if blocking_flags.intersection(flags):
        return None, {
            **record,
            "text": cleaned_text,
            "word_count": words,
            "char_count": chars,
            "quality_flags": flags,
            "drop_reason": "low_signal_text",
        }
    if words < config.min_words:
        return None, {**record, "text": cleaned_text, "word_count": words, "char_count": chars, "drop_reason": "too_few_words"}
    if chars < config.min_chars:
        return None, {**record, "text": cleaned_text, "word_count": words, "char_count": chars, "drop_reason": "too_few_characters"}

    return {
        **record,
        "text": cleaned_text,
        "word_count": words,
        "char_count": chars,
        "quality_flags": flags,
    }, None


def clean_records(records: list[dict], config: PipelineConfig) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    rejected: list[dict] = []
    for record in records:
        clean_record, rejected_record = clean_and_validate(record, config)
        if clean_record is not None:
            kept.append(clean_record)
        if rejected_record is not None:
            rejected.append(rejected_record)
    return kept, rejected
