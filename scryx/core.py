#!/usr/bin/env python3
"""Core crawling, filtering, and export logic for Scryx."""

from __future__ import annotations

import csv
import json
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = 10
DEFAULT_DELAY = 0.25
DEFAULT_MAX_PAGES = 25
MAX_CRAWL_DEPTH = 2
MAX_PAGE_LIMIT = 100
USER_AGENT = "Scryx/0.7.0 (+authorized-security-research)"


def normalize_url(base_url: str, href: str) -> str | None:
    """Return a normalized HTTP(S) URL or None for unsupported links."""
    href = href.strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None

    absolute = urljoin(base_url, href)
    clean, _fragment = urldefrag(absolute)
    parsed = urlparse(clean)

    if parsed.scheme not in {"http", "https"}:
        return None

    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if "..." in path_segments:
        return None

    return clean


def canonical_crawl_url(url: str) -> str:
    """Return a canonical URL used for crawl queue deduplication."""
    clean, _fragment = urldefrag(url)
    parsed = urlparse(clean)
    return parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=parsed.path or "/",
    ).geturl()


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract unique normalized links from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()

    for tag in soup.find_all("a", href=True):
        normalized = normalize_url(base_url, tag["href"])
        if normalized is not None:
            links.add(normalized)

    return sorted(links)


def is_internal_link(link: str, target_url: str) -> bool:
    """Return True when a link belongs to the same host as the target."""
    return urlparse(link).netloc.lower() == urlparse(target_url).netloc.lower()


def path_matches_prefix(link: str, path_prefix: str | None) -> bool:
    """Return True when a link path matches the optional prefix."""
    if not path_prefix:
        return True

    normalized_prefix = path_prefix if path_prefix.startswith("/") else f"/{path_prefix}"
    path = urlparse(link).path or "/"

    if normalized_prefix == "/":
        return True

    return path == normalized_prefix or path.startswith(normalized_prefix.rstrip("/") + "/")


def path_is_excluded(link: str, exclude_path_prefixes: list[str] | None) -> bool:
    """Return True when a link matches any excluded path prefix."""
    if not exclude_path_prefixes:
        return False

    return any(path_matches_prefix(link, prefix) for prefix in exclude_path_prefixes)


def normalize_extensions(extensions: list[str] | None) -> list[str]:
    """Normalize extensions to lowercase values beginning with a dot."""
    if not extensions:
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for extension in extensions:
        value = extension.strip().lower()
        if not value:
            continue
        if not value.startswith("."):
            value = f".{value}"
        if value not in seen:
            seen.add(value)
            normalized.append(value)

    return normalized


def has_excluded_extension(link: str, exclude_extensions: list[str] | None) -> bool:
    """Return True when a URL path ends with an excluded extension."""
    excluded = set(normalize_extensions(exclude_extensions))
    if not excluded:
        return False

    suffix = Path(urlparse(link).path).suffix.lower()
    return suffix in excluded


def classify_links(
    links: list[str],
    target_url: str,
    path_prefix: str | None = None,
    exclude_path_prefixes: list[str] | None = None,
    exclude_extensions: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Split links into internal and external groups."""
    internal: list[str] = []
    external: list[str] = []

    for link in links:
        if has_excluded_extension(link, exclude_extensions):
            continue

        if is_internal_link(link, target_url):
            if path_matches_prefix(link, path_prefix) and not path_is_excluded(
                link, exclude_path_prefixes
            ):
                internal.append(link)
        else:
            external.append(link)

    return internal, external


def scrape(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[list[str], str]:
    """Fetch one page and return discovered links plus the final response URL."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return extract_links(response.text, response.url), response.url


def crawl(
    url: str,
    depth: int,
    max_pages: int = DEFAULT_MAX_PAGES,
    timeout: int = DEFAULT_TIMEOUT,
    path_prefix: str | None = None,
    exclude_path_prefixes: list[str] | None = None,
    exclude_extensions: list[str] | None = None,
    delay: float = DEFAULT_DELAY,
) -> tuple[list[str], str, list[str], list[tuple[str, str]]]:
    """Crawl same-host links up to a bounded depth.

    External links are collected but never requested. When path_prefix is set,
    only matching internal links are eligible for additional requests.
    """
    start_url = canonical_crawl_url(url)
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    visited: set[str] = set()
    discovered: set[str] = set()
    errors: list[tuple[str, str]] = []
    first_final_url: str | None = None

    while queue and len(visited) < max_pages:
        current_url, current_depth = queue.popleft()
        if current_url in visited:
            continue

        visited.add(current_url)

        try:
            links, final_url = scrape(current_url, timeout=timeout)
        except requests.RequestException as exc:
            if current_url == start_url and first_final_url is None:
                raise
            errors.append((current_url, str(exc)))
            continue

        final_url = canonical_crawl_url(final_url)

        if first_final_url is None:
            first_final_url = final_url

        discovered.update(links)

        if current_depth >= depth:
            continue

        for link in links:
            if not is_internal_link(link, first_final_url):
                continue
            if not path_matches_prefix(link, path_prefix):
                continue
            if path_is_excluded(link, exclude_path_prefixes):
                continue
            if has_excluded_extension(link, exclude_extensions):
                continue
            crawl_link = canonical_crawl_url(link)
            if crawl_link not in visited:
                queue.append((crawl_link, current_depth + 1))

        if delay > 0 and queue and len(visited) < max_pages:
            time.sleep(delay)

    return sorted(discovered), first_final_url or start_url, sorted(visited), errors


def print_group(title: str, links: list[str]) -> None:
    """Print one categorized group of links."""
    print(f"\n[{title}] ({len(links)})")
    if not links:
        print("(none)")
        return

    for link in links:
        print(link)


def print_crawl_errors(errors: list[tuple[str, str]]) -> None:
    """Print failed crawl requests with their URL and reason."""
    if not errors:
        return

    print(f"\n[CRAWL ERRORS] ({len(errors)})")
    for error_url, message in errors:
        print(f"- {error_url}")
        print(f"  {message}")


def build_report(
    requested_url: str,
    final_url: str,
    all_links: list[str],
    internal: list[str],
    external: list[str],
    internal_only: bool,
    path_prefix: str | None,
    exclude_path_prefixes: list[str] | None = None,
    exclude_extensions: list[str] | None = None,
    depth: int = 0,
    pages_scanned: int = 1,
    max_pages: int = DEFAULT_MAX_PAGES,
    crawl_errors: list[tuple[str, str]] | None = None,
) -> dict:
    """Build a serializable report for JSON/CSV export."""
    visible_external = [] if internal_only else external
    crawl_errors = crawl_errors or []

    return {
        "requested_url": requested_url,
        "final_url": final_url,
        "total_found": len(all_links),
        "total_shown": len(internal) + len(visible_external),
        "filters": {
            "internal_only": internal_only,
            "path_prefix": path_prefix,
            "exclude_path_prefixes": exclude_path_prefixes or [],
            "exclude_extensions": normalize_extensions(exclude_extensions),
        },
        "crawl": {
            "depth": depth,
            "pages_attempted": pages_scanned,
            "pages_scanned": pages_scanned - len(crawl_errors),
            "failed_requests": len(crawl_errors),
            "max_pages": max_pages,
            "errors": [
                {"url": error_url, "error": message}
                for error_url, message in crawl_errors
            ],
        },
        "links": {
            "internal": internal,
            "external": visible_external,
        },
    }


def output_format_for_path(path: str | Path) -> str:
    """Infer the export format from the output filename."""
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".csv":
        return "csv"
    raise ValueError("Output file must end with .json or .csv")


def save_report(path: str | Path, report: dict) -> str:
    """Save a report as JSON or CSV and return the selected format."""
    output_path = Path(path)
    output_format = output_format_for_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "json":
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_format

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "url"])
        writer.writeheader()
        for category in ("internal", "external"):
            for link in report["links"][category]:
                writer.writerow({"category": category.upper(), "url": link})

    return output_format

