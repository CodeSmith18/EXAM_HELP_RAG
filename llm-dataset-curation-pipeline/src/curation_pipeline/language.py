from __future__ import annotations

from langdetect import DetectorFactory, LangDetectException, detect_langs

from .config import PipelineConfig

DetectorFactory.seed = 0


def detect_language(text: str) -> tuple[str, float]:
    sample = (text or "")[:5000]
    if not sample.strip():
        return "unknown", 0.0
    try:
        candidates = detect_langs(sample)
    except LangDetectException:
        return "unknown", 0.0
    if not candidates:
        return "unknown", 0.0
    best = candidates[0]
    return best.lang, float(best.prob)


def filter_by_language(records: list[dict], config: PipelineConfig) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    rejected: list[dict] = []
    allowlist = set(config.language_allowlist)

    for record in records:
        language, confidence = detect_language(record.get("text", ""))
        enriched = {**record, "language": language, "language_confidence": round(confidence, 4)}
        if allowlist and language not in allowlist:
            rejected.append({**enriched, "drop_reason": "language_not_allowed"})
            continue
        if confidence < config.language_min_confidence:
            rejected.append({**enriched, "drop_reason": "language_confidence_too_low"})
            continue
        kept.append(enriched)

    return kept, rejected

