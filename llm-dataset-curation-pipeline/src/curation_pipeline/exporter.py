from __future__ import annotations

from pathlib import Path

import pandas as pd
from datasets import Dataset

from .io_utils import write_jsonl


def export_jsonl(records: list[dict], path: str | Path) -> Path:
    return write_jsonl(path, records)


def export_parquet(records: list[dict], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(target, index=False)
    return target


def export_huggingface_dataset(records: list[dict], output_dir: str | Path) -> Path:
    target = Path(output_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    dataset = Dataset.from_list(records)
    dataset.save_to_disk(str(target))
    return target


def export_dataset(records: list[dict], output_dir: str | Path = "data/processed") -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    jsonl_path = export_jsonl(records, output / "curated_dataset.jsonl")
    parquet_path = export_parquet(records, output / "curated_dataset.parquet")
    hf_path = export_huggingface_dataset(records, output.parent / "huggingface" / "curated_dataset")
    return {
        "jsonl": str(jsonl_path),
        "parquet": str(parquet_path),
        "huggingface_dataset": str(hf_path),
    }

