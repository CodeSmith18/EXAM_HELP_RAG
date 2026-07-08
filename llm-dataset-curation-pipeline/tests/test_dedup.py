from curation_pipeline.config import PipelineConfig
from curation_pipeline.dedup import deduplicate_records


def make_record(url: str, text: str) -> dict:
    return {
        "source_url": url,
        "domain": "local_file",
        "title": "Test",
        "text": text,
        "language": "en",
        "language_confidence": 0.99,
        "word_count": len(text.split()),
        "char_count": len(text),
        "quality_flags": [],
        "fetched_at": "2026-01-01T00:00:00+00:00",
    }


def test_exact_dedup_removes_identical_normalized_text():
    text = "Dataset curation keeps high quality records and removes duplicate training examples." * 10
    config = PipelineConfig(seed_urls=["file:///tmp/example.html"])

    kept, stats = deduplicate_records(
        [
            make_record("file:///one.html", text),
            make_record("file:///two.html", f"  {text}\n"),
        ],
        config,
    )

    assert len(kept) == 1
    assert stats["exact_duplicate_count"] == 1
    assert stats["duplicate_examples"][0]["reason"] == "exact_duplicate"


def test_minhash_dedup_catches_near_duplicate_text():
    base = (
        "Dataset curation for foundation models keeps useful text, removes noisy records, stores provenance, "
        "tracks language, checks source metadata, and exports clean JSONL and Parquet datasets for model training. "
    ) * 8
    near = base.replace("useful text", "valuable text", 1).replace("model training", "training workflows", 1)
    config = PipelineConfig(seed_urls=["file:///tmp/example.html"], near_duplicate_threshold=0.75)

    kept, stats = deduplicate_records(
        [
            make_record("file:///one.html", base),
            make_record("file:///two.html", near),
        ],
        config,
    )

    assert len(kept) == 1
    assert stats["near_duplicate_count"] == 1
    assert stats["duplicate_examples"][0]["reason"] == "near_duplicate"
