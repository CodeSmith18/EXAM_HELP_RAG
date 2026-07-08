from curation_pipeline.cleaner import clean_and_validate
from curation_pipeline.config import PipelineConfig
from curation_pipeline.extractor import extract_text_from_html
from curation_pipeline.language import detect_language, filter_by_language


def test_html_extractor_removes_boilerplate_and_keeps_main_text():
    html = """
    <html>
      <head><title>Useful Title</title><script>bad()</script></head>
      <body>
        <nav>Navigation text</nav>
        <main><h1>Main</h1><p>Useful article text remains here.</p></main>
        <footer>Footer text</footer>
      </body>
    </html>
    """

    title, text = extract_text_from_html(html)

    assert title == "Useful Title"
    assert "Useful article text remains here" in text
    assert "Navigation text" not in text
    assert "Footer text" not in text
    assert "bad()" not in text


def test_quality_filter_drops_noisy_text():
    config = PipelineConfig(seed_urls=["file:///tmp/example.html"], min_words=5, min_chars=20)
    noisy_text = "!!!! ???? //// " * 30

    kept, rejected = clean_and_validate({"source_url": "file:///noisy.html", "text": noisy_text}, config)

    assert kept is None
    assert rejected is not None
    assert rejected["drop_reason"] == "low_signal_text"
    assert "low_alpha_ratio" in rejected["quality_flags"]


def test_language_detector_accepts_english_and_rejects_unsupported_language():
    english = (
        "This is a clear English paragraph about dataset curation, quality filtering, metadata, provenance, "
        "and reproducible machine learning workflows. "
    ) * 8
    french = (
        "Ceci est un paragraphe francais sur la preparation des donnees, la qualite, les metadonnees, "
        "et les flux de travail reproductibles. "
    ) * 8
    config = PipelineConfig(seed_urls=["file:///tmp/example.html"], language_allowlist=["en"], min_words=5, min_chars=20)

    language, confidence = detect_language(english)
    kept, rejected = filter_by_language(
        [
            {"source_url": "file:///english.html", "text": english},
            {"source_url": "file:///french.html", "text": french},
        ],
        config,
    )

    assert language == "en"
    assert confidence >= 0.70
    assert len(kept) == 1
    assert kept[0]["language"] == "en"
    assert len(rejected) == 1
    assert rejected[0]["drop_reason"] == "language_not_allowed"

