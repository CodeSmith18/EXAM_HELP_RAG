from __future__ import annotations

import re
from typing import Iterable

from datasketch import MinHash, MinHashLSH

from .cleaner import normalize_for_hash
from .config import PipelineConfig
from .schema import sha256_text


def tokenize_words(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", normalize_for_hash(text))


def make_shingles(tokens: list[str], shingle_size: int) -> set[str]:
    if len(tokens) < shingle_size:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[index : index + shingle_size]) for index in range(len(tokens) - shingle_size + 1)}


def build_minhash(shingles: Iterable[str], num_perm: int = 128) -> MinHash:
    minhash = MinHash(num_perm=num_perm)
    for shingle in shingles:
        minhash.update(shingle.encode("utf-8"))
    return minhash


def deduplicate_records(records: list[dict], config: PipelineConfig) -> tuple[list[dict], dict]:
    seen_hashes: dict[str, dict] = {}
    exact_kept: list[dict] = []
    duplicate_examples: list[dict] = []
    exact_duplicate_count = 0

    for record in records:
        normalized = normalize_for_hash(record.get("text", ""))
        content_hash = sha256_text(normalized)
        enriched = {**record, "content_hash": content_hash}
        if content_hash in seen_hashes:
            exact_duplicate_count += 1
            if len(duplicate_examples) < 10:
                duplicate_examples.append(
                    {
                        "reason": "exact_duplicate",
                        "kept_url": seen_hashes[content_hash].get("source_url"),
                        "dropped_url": record.get("source_url"),
                    }
                )
            continue
        seen_hashes[content_hash] = enriched
        exact_kept.append(enriched)

    lsh = MinHashLSH(threshold=config.near_duplicate_threshold, num_perm=128)
    kept: list[dict] = []
    inserted: dict[str, dict] = {}
    near_duplicate_count = 0

    for index, record in enumerate(exact_kept):
        tokens = tokenize_words(record.get("text", ""))
        shingles = make_shingles(tokens, config.shingle_size)
        if not shingles:
            continue
        minhash = build_minhash(shingles)
        matches = lsh.query(minhash)
        if matches:
            near_duplicate_count += 1
            if len(duplicate_examples) < 10:
                matched_key = matches[0]
                duplicate_examples.append(
                    {
                        "reason": "near_duplicate",
                        "kept_url": inserted[matched_key].get("source_url"),
                        "dropped_url": record.get("source_url"),
                    }
                )
            continue
        key = f"record-{index}"
        lsh.insert(key, minhash)
        inserted[key] = record
        kept.append(record)

    stats = {
        "input_count": len(records),
        "after_exact_dedup_count": len(exact_kept),
        "final_count": len(kept),
        "exact_duplicate_count": exact_duplicate_count,
        "near_duplicate_count": near_duplicate_count,
        "duplicate_examples": duplicate_examples,
    }
    return kept, stats

