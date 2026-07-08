from pathlib import Path

from curation_pipeline.cli import main


def test_cli_all_runs_end_to_end_with_local_html_fixture(tmp_path: Path, monkeypatch):
    fixture_dir = Path(__file__).parent / "fixtures"
    page1_url = (fixture_dir / "page1.html").resolve().as_uri()
    config_path = tmp_path / "seeds.yml"
    config_path.write_text(
        f"""
project_name: fixture_curation_demo
allowed_domains: []
seed_urls:
  - {page1_url}
max_pages: 5
max_depth: 1
request_delay_seconds: 0
language_allowlist:
  - en
license: fixture
source_type: local_fixture
min_words: 40
min_chars: 200
near_duplicate_threshold: 0.75
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    main(["all", "--config", str(config_path)])

    assert (tmp_path / "data/processed/curated_dataset.jsonl").exists()
    assert (tmp_path / "data/processed/curated_dataset.parquet").exists()
    assert (tmp_path / "reports/dataset_quality.md").exists()
    assert (tmp_path / "reports/dataset_quality.json").exists()
    assert (tmp_path / "data/processed/rejected_records.jsonl").exists()
    assert (tmp_path / "data/processed/dedup_report.json").exists()

