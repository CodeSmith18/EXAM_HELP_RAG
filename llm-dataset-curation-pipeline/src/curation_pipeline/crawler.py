from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from .config import PipelineConfig
from .io_utils import write_json, write_jsonl
from .schema import RawPage, domain_from_url, now_utc_iso


def is_allowed_url(url: str, allowed_domains: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return True
    if parsed.scheme not in {"http", "https"}:
        return False
    if not allowed_domains:
        return True
    domain = parsed.netloc.lower()
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains)


def normalize_url(url: str) -> str:
    return urldefrag(url)[0].rstrip("/")


def extract_links(html: str, base_url: str, allowed_domains: list[str]) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        candidate = normalize_url(urljoin(base_url, href))
        if candidate in seen or not is_allowed_url(candidate, allowed_domains):
            continue
        seen.add(candidate)
        links.append(candidate)
    return links


def fetch_url(url: str, config: PipelineConfig) -> RawPage:
    parsed = urlparse(url)
    fetched_at = now_utc_iso()
    if parsed.scheme == "file":
        try:
            html = Path(parsed.path).read_text(encoding="utf-8")
            return RawPage(
                url=url,
                final_url=url,
                status_code=200,
                fetched_at=fetched_at,
                content_type="text/html",
                html=html,
            )
        except OSError as exc:
            return RawPage(
                url=url,
                final_url=url,
                status_code=0,
                fetched_at=fetched_at,
                content_type=None,
                html="",
                error=str(exc),
            )

    headers = {"User-Agent": config.user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        content_type = response.headers.get("content-type", "")
        html = response.text if "text/html" in content_type.lower() else ""
        return RawPage(
            url=url,
            final_url=response.url,
            status_code=response.status_code,
            fetched_at=fetched_at,
            content_type=content_type,
            html=html,
        )
    except requests.RequestException as exc:
        return RawPage(
            url=url,
            final_url=url,
            status_code=0,
            fetched_at=fetched_at,
            content_type=None,
            html="",
            error=str(exc),
        )


def crawl(config: PipelineConfig) -> tuple[list[dict], dict]:
    queue: deque[tuple[str, int]] = deque((normalize_url(url), 0) for url in config.seed_urls)
    visited: set[str] = set()
    discovered: set[str] = {normalize_url(url) for url in config.seed_urls}
    raw_pages: list[dict] = []

    progress = tqdm(total=config.max_pages, desc="Crawling", unit="page")
    while queue and len(raw_pages) < config.max_pages:
        url, depth = queue.popleft()
        if url in visited or not is_allowed_url(url, config.allowed_domains):
            continue

        visited.add(url)
        page = fetch_url(url, config)
        page.depth = depth
        raw_pages.append(page.model_dump(mode="json"))
        progress.update(1)

        if page.status_code == 200 and page.html and depth < config.max_depth:
            for link in extract_links(page.html, page.final_url, config.allowed_domains):
                if link not in discovered and len(discovered) < config.max_pages * 10:
                    discovered.add(link)
                    queue.append((link, depth + 1))

        if config.request_delay_seconds > 0 and queue and urlparse(url).scheme != "file":
            time.sleep(config.request_delay_seconds)

    progress.close()
    stats = {
        "project_name": config.project_name,
        "total_urls_discovered": len(discovered),
        "pages_attempted": len(visited),
        "pages_fetched_successfully": sum(1 for page in raw_pages if page["status_code"] == 200),
        "allowed_domains": config.allowed_domains,
        "seed_urls": config.seed_urls,
        "generated_at": now_utc_iso(),
    }
    return raw_pages, stats


def crawl_to_disk(config: PipelineConfig, output_path: str | Path = "data/raw/pages.jsonl") -> tuple[Path, Path]:
    raw_pages, stats = crawl(config)
    pages_path = write_jsonl(output_path, raw_pages)
    stats_path = write_json(Path(output_path).with_name("crawl_stats.json"), stats)
    return pages_path, stats_path

