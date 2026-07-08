from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
import yaml

from curation_pipeline.cli import curate_raw_pages
from curation_pipeline.config import PipelineConfig, load_config
from curation_pipeline.crawler import crawl_to_disk
from curation_pipeline.io_utils import read_jsonl
from curation_pipeline.report import report_from_disk

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "seeds.example.yml"
RUNS_DIR = PROJECT_ROOT / "data" / "ui_runs"


def load_default_config() -> PipelineConfig:
    return load_config(DEFAULT_CONFIG_PATH)


def split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")


def discover_runs() -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    return sorted([path for path in RUNS_DIR.iterdir() if path.is_dir()], reverse=True)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def make_config(default: PipelineConfig) -> PipelineConfig:
    st.sidebar.header("Run Config")
    project_name = st.sidebar.text_input("Project", value=default.project_name)
    seed_urls = st.sidebar.text_area("Seed URLs", value="\n".join(default.seed_urls), height=120)
    allowed_domains = st.sidebar.text_area("Allowed Domains", value="\n".join(default.allowed_domains), height=80)

    st.sidebar.divider()
    max_pages = st.sidebar.slider("Max Pages", min_value=1, max_value=100, value=default.max_pages)
    max_depth = st.sidebar.slider("Max Depth", min_value=0, max_value=3, value=default.max_depth)
    request_delay_seconds = st.sidebar.number_input(
        "Request Delay Seconds",
        min_value=0.0,
        max_value=10.0,
        value=float(default.request_delay_seconds),
        step=0.5,
    )

    st.sidebar.divider()
    language_allowlist = st.sidebar.text_input("Languages", value=",".join(default.language_allowlist))
    min_words = st.sidebar.number_input("Min Words", min_value=1, max_value=1000, value=default.min_words, step=10)
    min_chars = st.sidebar.number_input("Min Characters", min_value=1, max_value=5000, value=default.min_chars, step=100)
    near_duplicate_threshold = st.sidebar.slider(
        "Near Duplicate Threshold",
        min_value=0.50,
        max_value=0.99,
        value=float(default.near_duplicate_threshold),
        step=0.01,
    )

    st.sidebar.divider()
    license_name = st.sidebar.text_input("License", value=default.license)
    source_type = st.sidebar.text_input("Source Type", value=default.source_type)

    config = PipelineConfig(
        project_name=project_name,
        allowed_domains=split_lines(allowed_domains),
        seed_urls=split_lines(seed_urls),
        max_pages=max_pages,
        max_depth=max_depth,
        request_delay_seconds=request_delay_seconds,
        language_allowlist=[item.strip() for item in language_allowlist.split(",") if item.strip()],
        license=license_name,
        source_type=source_type,
        min_words=min_words,
        min_chars=min_chars,
        near_duplicate_threshold=near_duplicate_threshold,
    )
    return config


def validate_config(config: PipelineConfig) -> list[str]:
    errors: list[str] = []
    if not config.seed_urls:
        errors.append("Add at least one seed URL.")
    for url in config.seed_urls:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https", "file"}:
            errors.append(f"Unsupported URL scheme: {url}")
    return errors


def run_pipeline(config: PipelineConfig) -> dict[str, str]:
    current_run_dir = RUNS_DIR / run_id()
    raw_path = current_run_dir / "raw" / "pages.jsonl"
    processed_dir = current_run_dir / "processed"
    report_dir = current_run_dir / "reports"

    raw_output, crawl_stats = crawl_to_disk(config, raw_path)
    output_paths = curate_raw_pages(raw_output, config, processed_dir)
    report_paths = report_from_disk(
        output_paths["jsonl"],
        rejected_path=output_paths["rejected"],
        dedup_path=output_paths["dedup_report"],
        crawl_stats_path=crawl_stats,
        output_dir=report_dir,
    )

    return {
        "run_dir": str(current_run_dir),
        "raw": str(raw_output),
        "crawl_stats": str(crawl_stats),
        **output_paths,
        **{f"report_{key}": value for key, value in report_paths.items()},
    }


def metrics_row(report: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fetched", report.get("pages_fetched_successfully", 0))
    col2.metric("Curated", report.get("records_after_deduplication", 0))
    col3.metric("Rejected", sum(report.get("pages_dropped_by_reason", {}).values()))
    col4.metric(
        "Duplicates",
        report.get("exact_duplicate_count", 0) + report.get("near_duplicate_count", 0),
    )


def render_report(paths: dict[str, str]) -> None:
    report_json_path = Path(paths["report_json"])
    report = read_json(report_json_path)
    if report:
        metrics_row(report)

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Quality Report")
        if report:
            st.write("Drop reasons")
            st.dataframe(
                pd.DataFrame(
                    [{"reason": key, "count": value} for key, value in report.get("pages_dropped_by_reason", {}).items()]
                ),
                use_container_width=True,
                hide_index=True,
            )
            st.write("Language distribution")
            st.dataframe(
                pd.DataFrame(
                    [{"language": key, "count": value} for key, value in report.get("language_distribution", {}).items()]
                ),
                use_container_width=True,
                hide_index=True,
            )
            st.write("Text statistics")
            st.json(
                {
                    "word_count": report.get("word_count", {}),
                    "char_count": report.get("char_count", {}),
                    "duplicate_examples": report.get("duplicate_examples", []),
                }
            )
    with right:
        st.subheader("Artifacts")
        for label, key in [
            ("JSONL", "jsonl"),
            ("Parquet", "parquet"),
            ("Report JSON", "report_json"),
            ("Report Markdown", "report_markdown"),
        ]:
            path = Path(paths[key])
            if path.exists():
                st.caption(label)
                st.code(str(path.relative_to(PROJECT_ROOT)), language="text")
                st.download_button(
                    f"Download {label}",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime="application/octet-stream",
                    key=f"download-{label}-{path}",
                )


def render_dataset_preview(jsonl_path: Path) -> None:
    if not jsonl_path.exists():
        st.info("No curated dataset found for this run.")
        return

    records = read_jsonl(jsonl_path)
    if not records:
        st.warning("The curated dataset is empty.")
        return

    preview_columns = ["title", "source_url", "language", "word_count", "char_count"]
    frame = pd.DataFrame(records)
    st.subheader("Dataset Preview")
    st.dataframe(frame[preview_columns], use_container_width=True, hide_index=True)

    selected_title = st.selectbox("Record", frame["title"].fillna("").tolist())
    selected = next(record for record in records if record.get("title", "") == selected_title)
    st.text_area("Text Preview", selected.get("text", "")[:5000], height=260)
    st.json({key: selected[key] for key in selected if key != "text"})


def render_existing_runs() -> None:
    runs = discover_runs()
    if not runs:
        st.info("No UI runs yet.")
        return

    run = st.selectbox("Run", runs, format_func=lambda path: path.name)
    paths = {
        "jsonl": str(run / "processed" / "curated_dataset.jsonl"),
        "parquet": str(run / "processed" / "curated_dataset.parquet"),
        "report_json": str(run / "reports" / "dataset_quality.json"),
        "report_markdown": str(run / "reports" / "dataset_quality.md"),
    }
    render_report(paths)
    render_dataset_preview(Path(paths["jsonl"]))


def main() -> None:
    st.set_page_config(page_title="LLM Dataset Curator", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        div[data-testid="stMetric"] {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 12px 14px;
          background: #ffffff;
        }
        .stButton > button {
          border-radius: 8px;
          font-weight: 650;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    default = load_default_config()
    config = make_config(default)

    st.title("LLM Dataset Curator")
    tabs = st.tabs(["Run Pipeline", "Explore Results", "Config"])

    with tabs[0]:
        errors = validate_config(config)
        if errors:
            for error in errors:
                st.error(error)
        run_button = st.button("Run Pipeline", type="primary", disabled=bool(errors))
        if run_button:
            with st.spinner("Running curation pipeline..."):
                paths = run_pipeline(config)
                st.session_state["latest_paths"] = paths
            st.success("Pipeline run complete.")
            render_report(st.session_state["latest_paths"])
            render_dataset_preview(Path(st.session_state["latest_paths"]["jsonl"]))

    with tabs[1]:
        if "latest_paths" in st.session_state:
            render_report(st.session_state["latest_paths"])
            render_dataset_preview(Path(st.session_state["latest_paths"]["jsonl"]))
        else:
            render_existing_runs()

    with tabs[2]:
        st.subheader("Resolved Config")
        st.code(yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False), language="yaml")


if __name__ == "__main__":
    main()
