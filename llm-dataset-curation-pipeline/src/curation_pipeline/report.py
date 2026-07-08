from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io_utils import read_jsonl, write_json
from .quality import distribution, drop_reason_distribution, numeric_summary
from .schema import CuratedRecord, now_utc_iso


def load_optional_json(path: str | Path | None) -> dict:
    if path is None or not Path(path).exists():
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_optional_jsonl(path: str | Path | None) -> list[dict]:
    if path is None or not Path(path).exists():
        return []
    return read_jsonl(path)


def build_quality_report(
    curated_records: list[dict],
    rejected_records: list[dict] | None = None,
    dedup_stats: dict[str, Any] | None = None,
    crawl_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rejected_records = rejected_records or []
    dedup_stats = dedup_stats or {}
    crawl_stats = crawl_stats or {}

    schema_fields = list(CuratedRecord.model_fields.keys())
    return {
        "generated_at": now_utc_iso(),
        "total_urls_discovered": crawl_stats.get("total_urls_discovered", 0),
        "pages_fetched_successfully": crawl_stats.get("pages_fetched_successfully", 0),
        "records_before_deduplication": dedup_stats.get("input_count", len(curated_records)),
        "records_after_deduplication": len(curated_records),
        "exact_duplicate_count": dedup_stats.get("exact_duplicate_count", 0),
        "near_duplicate_count": dedup_stats.get("near_duplicate_count", 0),
        "pages_dropped_by_reason": drop_reason_distribution(rejected_records),
        "language_distribution": distribution(curated_records, "language"),
        "domain_distribution": distribution(curated_records, "domain"),
        "word_count": numeric_summary(curated_records, "word_count"),
        "char_count": numeric_summary(curated_records, "char_count"),
        "duplicate_examples": dedup_stats.get("duplicate_examples", []),
        "final_schema": schema_fields,
        "sample_curated_record": curated_records[0] if curated_records else {},
    }


def report_to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dataset Quality Report",
        "",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Crawl Summary",
        "",
        f"- Total URLs discovered: **{report['total_urls_discovered']}**",
        f"- Pages fetched successfully: **{report['pages_fetched_successfully']}**",
        "",
        "## Curation Summary",
        "",
        f"- Records before deduplication: **{report['records_before_deduplication']}**",
        f"- Records after deduplication: **{report['records_after_deduplication']}**",
        f"- Exact duplicates removed: **{report['exact_duplicate_count']}**",
        f"- Near duplicates removed: **{report['near_duplicate_count']}**",
        "",
        "## Drop Reasons",
        "",
    ]

    drop_reasons = report["pages_dropped_by_reason"] or {"none": 0}
    lines.extend(f"- {reason}: {count}" for reason, count in drop_reasons.items())

    lines.extend(
        [
            "",
            "## Language Distribution",
            "",
        ]
    )
    lines.extend(f"- {language}: {count}" for language, count in (report["language_distribution"] or {}).items())

    lines.extend(
        [
            "",
            "## Domain Distribution",
            "",
        ]
    )
    lines.extend(f"- {domain}: {count}" for domain, count in (report["domain_distribution"] or {}).items())

    lines.extend(
        [
            "",
            "## Text Statistics",
            "",
            f"- Word count: `{report['word_count']}`",
            f"- Character count: `{report['char_count']}`",
            "",
            "## Duplicate Examples",
            "",
        ]
    )
    examples = report["duplicate_examples"] or []
    if examples:
        for example in examples:
            lines.append(f"- {example['reason']}: kept `{example.get('kept_url')}`, dropped `{example.get('dropped_url')}`")
    else:
        lines.append("- No duplicate examples captured.")

    lines.extend(
        [
            "",
            "## Final Schema",
            "",
            "```text",
            "\n".join(report["final_schema"]),
            "```",
            "",
            "## Sample Curated Record",
            "",
            "```json",
            json.dumps(report["sample_curated_record"], ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: dict[str, Any], output_dir: str | Path = "reports") -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = write_json(output / "dataset_quality.json", report)
    markdown_path = output / "dataset_quality.md"
    markdown_path.write_text(report_to_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}


def report_from_disk(
    curated_path: str | Path,
    rejected_path: str | Path | None = None,
    dedup_path: str | Path | None = None,
    crawl_stats_path: str | Path | None = None,
    output_dir: str | Path = "reports",
) -> dict[str, str]:
    curated_records = read_jsonl(curated_path)
    rejected_records = load_optional_jsonl(rejected_path)
    dedup_stats = load_optional_json(dedup_path)
    crawl_stats = load_optional_json(crawl_stats_path)
    report = build_quality_report(curated_records, rejected_records, dedup_stats, crawl_stats)
    return write_report(report, output_dir)

