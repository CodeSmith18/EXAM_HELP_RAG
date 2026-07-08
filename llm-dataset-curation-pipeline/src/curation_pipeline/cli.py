from __future__ import annotations

import argparse
from pathlib import Path

from .cleaner import clean_records
from .config import PipelineConfig, load_config
from .crawler import crawl_to_disk
from .dedup import deduplicate_records
from .exporter import export_dataset
from .extractor import extract_pages
from .io_utils import read_jsonl, write_json, write_jsonl
from .language import filter_by_language
from .report import report_from_disk
from .schema import CuratedRecord, PIPELINE_VERSION, now_utc_iso, sha256_text


def default_config_path() -> Path:
    return Path("configs/seeds.example.yml")


def enrich_final_records(records: list[dict], config: PipelineConfig) -> list[dict]:
    processed_at = now_utc_iso()
    final_records: list[dict] = []
    for record in records:
        stable_source = f"{record.get('source_url', '')}:{record.get('content_hash', '')}"
        payload = {
            "id": sha256_text(stable_source),
            "source_url": record["source_url"],
            "domain": record.get("domain", ""),
            "title": record.get("title", ""),
            "text": record["text"],
            "language": record.get("language", "unknown"),
            "language_confidence": float(record.get("language_confidence", 0.0)),
            "license": config.license,
            "source_type": config.source_type,
            "fetched_at": record.get("fetched_at", ""),
            "processed_at": processed_at,
            "content_hash": record["content_hash"],
            "word_count": int(record.get("word_count", 0)),
            "char_count": int(record.get("char_count", 0)),
            "quality_flags": record.get("quality_flags", []),
            "pipeline_version": PIPELINE_VERSION,
        }
        final_records.append(CuratedRecord(**payload).model_dump(mode="json"))
    return final_records


def curate_raw_pages(
    raw_input: str | Path,
    config: PipelineConfig,
    processed_dir: str | Path = "data/processed",
) -> dict[str, str]:
    raw_pages = read_jsonl(raw_input)
    fetched_pages = [page for page in raw_pages if page.get("status_code") == 200 and page.get("html")]
    fetch_rejections = [
        {"source_url": page.get("final_url") or page.get("url"), "drop_reason": "fetch_failed", **page}
        for page in raw_pages
        if page.get("status_code") != 200 or not page.get("html")
    ]

    extracted = extract_pages(fetched_pages)
    cleaned, rejected_cleaning = clean_records(extracted, config)
    language_kept, rejected_language = filter_by_language(cleaned, config)
    deduped, dedup_stats = deduplicate_records(language_kept, config)
    final_records = enrich_final_records(deduped, config)

    processed = Path(processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    rejected_records = fetch_rejections + rejected_cleaning + rejected_language
    write_jsonl(processed / "rejected_records.jsonl", rejected_records)
    write_json(processed / "dedup_report.json", dedup_stats)
    export_paths = export_dataset(final_records, processed)
    return {
        **export_paths,
        "rejected": str(processed / "rejected_records.jsonl"),
        "dedup_report": str(processed / "dedup_report.json"),
    }


def infer_artifact_paths(curated_input: str | Path) -> tuple[Path, Path, Path]:
    curated_path = Path(curated_input)
    processed_dir = curated_path.parent
    data_dir = processed_dir.parent
    return (
        processed_dir / "rejected_records.jsonl",
        processed_dir / "dedup_report.json",
        data_dir / "raw" / "crawl_stats.json",
    )


def run_all(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    raw_path, stats_path = crawl_to_disk(config, args.raw_output)
    paths = curate_raw_pages(raw_path, config, args.processed_dir)
    report_from_disk(
        paths["jsonl"],
        rejected_path=paths["rejected"],
        dedup_path=paths["dedup_report"],
        crawl_stats_path=stats_path,
        output_dir=args.report_dir,
    )
    print(f"Pipeline complete. Curated dataset: {paths['jsonl']}")


def run_crawl(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    raw_path, stats_path = crawl_to_disk(config, args.output)
    print(f"Crawl complete. Raw pages: {raw_path}; stats: {stats_path}")


def run_curate(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    paths = curate_raw_pages(args.input, config, args.processed_dir)
    print(f"Curation complete. Curated dataset: {paths['jsonl']}")


def run_report(args: argparse.Namespace) -> None:
    rejected_path, dedup_path, crawl_stats_path = infer_artifact_paths(args.input)
    paths = report_from_disk(
        args.input,
        rejected_path=args.rejected or rejected_path,
        dedup_path=args.dedup_report or dedup_path,
        crawl_stats_path=args.crawl_stats or crawl_stats_path,
        output_dir=args.output_dir,
    )
    print(f"Report complete. Markdown: {paths['markdown']}; JSON: {paths['json']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Curate public web pages into LLM-ready datasets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    all_parser = subparsers.add_parser("all", help="Run crawl, curate, export, and report stages.")
    all_parser.add_argument("--config", default=default_config_path(), type=Path)
    all_parser.add_argument("--raw-output", default=Path("data/raw/pages.jsonl"), type=Path)
    all_parser.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    all_parser.add_argument("--report-dir", default=Path("reports"), type=Path)
    all_parser.set_defaults(func=run_all)

    crawl_parser = subparsers.add_parser("crawl", help="Fetch public web pages into raw JSONL.")
    crawl_parser.add_argument("--config", default=default_config_path(), type=Path)
    crawl_parser.add_argument("--output", default=Path("data/raw/pages.jsonl"), type=Path)
    crawl_parser.set_defaults(func=run_crawl)

    curate_parser = subparsers.add_parser("curate", help="Curate raw crawled pages into JSONL and Parquet.")
    curate_parser.add_argument("--input", required=True, type=Path)
    curate_parser.add_argument("--config", default=default_config_path(), type=Path)
    curate_parser.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    curate_parser.set_defaults(func=run_curate)

    report_parser = subparsers.add_parser("report", help="Generate quality reports for a curated dataset.")
    report_parser.add_argument("--input", required=True, type=Path)
    report_parser.add_argument("--output-dir", default=Path("reports"), type=Path)
    report_parser.add_argument("--rejected", default=None, type=Path)
    report_parser.add_argument("--dedup-report", default=None, type=Path)
    report_parser.add_argument("--crawl-stats", default=None, type=Path)
    report_parser.set_defaults(func=run_report)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

