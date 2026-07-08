from curation_pipeline.cleaner import clean_text, clean_records
from curation_pipeline.config import PipelineConfig


def test_clean_text_normalizes_whitespace():
    assert clean_text("  Hello\t\tworld.\n\n\nThis   is clean.  ") == "Hello world.\nThis is clean."


def test_clean_records_removes_empty_and_short_records():
    config = PipelineConfig(seed_urls=["file:///tmp/example.html"], min_words=5, min_chars=20)
    records = [
        {"source_url": "file:///empty.html", "text": "   "},
        {"source_url": "file:///short.html", "text": "too short"},
        {"source_url": "file:///good.html", "text": "This record contains enough useful English words for testing."},
    ]

    kept, rejected = clean_records(records, config)

    assert len(kept) == 1
    assert kept[0]["word_count"] >= 5
    assert [record["drop_reason"] for record in rejected] == ["empty_text", "too_few_words"]

