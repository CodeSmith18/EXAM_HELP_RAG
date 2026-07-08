from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .schema import domain_from_url

UNWANTED_SELECTORS = [
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "form",
    "aside",
    "iframe",
    "svg",
    "[hidden]",
    "[aria-hidden='true']",
]


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def extract_text_from_html(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html or "", "html.parser")

    for selector in UNWANTED_SELECTORS:
        for element in soup.select(selector):
            element.decompose()

    for element in soup.find_all(style=True):
        if element.attrs is None:
            continue
        style = str(element.get("style", "")).replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            element.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        heading = soup.find("h1")
        title = heading.get_text(" ", strip=True) if heading else ""

    content_root = soup.find("main") or soup.find("article") or soup.body or soup
    text = normalize_whitespace(content_root.get_text("\n", strip=True))
    return title, text


def extract_page(raw_page: dict) -> dict:
    title, text = extract_text_from_html(raw_page.get("html", ""))
    final_url = raw_page.get("final_url") or raw_page.get("url", "")
    return {
        "source_url": final_url,
        "original_url": raw_page.get("url", final_url),
        "domain": domain_from_url(final_url),
        "title": title,
        "text": text,
        "fetched_at": raw_page.get("fetched_at", ""),
        "status_code": raw_page.get("status_code", 0),
        "content_type": raw_page.get("content_type"),
        "crawl_depth": raw_page.get("depth", 0),
        "error": raw_page.get("error"),
    }


def extract_pages(raw_pages: list[dict]) -> list[dict]:
    return [extract_page(page) for page in raw_pages]
