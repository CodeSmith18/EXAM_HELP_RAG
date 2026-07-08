from pathlib import Path

import pandas as pd
from datasets import load_dataset

from curation_pipeline.exporter import export_dataset


def test_exporter_writes_jsonl_parquet_and_huggingface_loadable_json(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf_home"))
    monkeypatch.setenv("HF_DATASETS_CACHE", str(tmp_path / "hf_datasets_cache"))
    records = [
        {
            "id": "abc",
            "source_url": "file:///one.html",
            "domain": "local_file",
            "title": "One",
            "text": "Dataset curation creates clean training records.",
            "language": "en",
            "language_confidence": 0.99,
            "license": "test",
            "source_type": "fixture",
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "processed_at": "2026-01-01T00:00:00+00:00",
            "content_hash": "hash",
            "word_count": 6,
            "char_count": 48,
            "quality_flags": [],
            "pipeline_version": "0.1.0",
        }
    ]

    paths = export_dataset(records, tmp_path / "processed")

    assert Path(paths["jsonl"]).exists()
    assert Path(paths["parquet"]).exists()
    assert Path(paths["huggingface_dataset"]).exists()
    assert len(pd.read_parquet(paths["parquet"])) == 1

    dataset = load_dataset("json", data_files=paths["jsonl"], split="train", cache_dir=str(tmp_path / "hf_cache"))

    assert len(dataset) == 1
    assert dataset[0]["source_url"] == "file:///one.html"
