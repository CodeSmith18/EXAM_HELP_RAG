from __future__ import annotations

import re
from pathlib import Path

import fitz


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_pages(file_path: Path) -> list[dict[str, str | int]]:
    pages: list[dict[str, str | int]] = []
    with fitz.open(file_path) as doc:
        for index, page in enumerate(doc, start=1):
            text = clean_text(page.get_text("text"))
            pages.append({"page_number": index, "text": text})
    return pages
