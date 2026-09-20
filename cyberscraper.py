#!/usr/bin/env python3
"""CyberScraper - a small link discovery tool for authorized reconnaissance."""

from __future__ import annotations

import argparse
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = 10
USER_AGENT = "CyberScraper/0.1 (+authorized-security-research)"


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

    return clean


def extract_links(html: str, base_url: str, internal_only: bool = False) -> list[str]:
    """Extract unique links from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc.lower()
    links: set[str] = set()

    for tag in soup.find_all("a", href=True):
        normalized = normalize_url(base_url, tag["href"])
        if normalized is None:
            continue

        if internal_only and urlparse(normalized).netloc.lower() != base_host:
            continue

        links.add(normalized)

    return sorted(links)


def scrape(url: str, internal_only: bool = False, timeout: int = DEFAULT_TIMEOUT) -> list[str]:
    """Fetch one page and return discovered links."""
    headers = {"User-Agent": USER_AGENT}

    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    return extract_links(response.text, response.url, internal_only=internal_only)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract links from a web page for authorized reconnaissance."
    )
    parser.add_argument("url", help="Target page URL, e.g. https://example.com")
    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Show only links that belong to the target host.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        links = scrape(
            args.url,
            internal_only=args.internal_only,
            timeout=args.timeout,
        )
    except requests.RequestException as exc:
        print(f"[!] Request failed: {exc}")
        return 1

    print(f"[+] Found {len(links)} unique link(s)")
    for link in links:
        print(link)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
