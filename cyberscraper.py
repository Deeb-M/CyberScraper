#!/usr/bin/env python3
"""CyberScraper - a small link discovery tool for authorized reconnaissance."""

from __future__ import annotations

import argparse
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = 10
USER_AGENT = "CyberScraper/0.2 (+authorized-security-research)"


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


def classify_links(
    links: list[str],
    target_url: str,
    path_prefix: str | None = None,
) -> tuple[list[str], list[str]]:
    """Split links into internal and external groups.

    When path_prefix is supplied, it restricts only the internal links.
    External links are still reported so the user can see off-site references.
    """
    internal: list[str] = []
    external: list[str] = []

    for link in links:
        if is_internal_link(link, target_url):
            if path_matches_prefix(link, path_prefix):
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


def print_group(title: str, links: list[str]) -> None:
    """Print one categorized group of links."""
    print(f"\n[{title}] ({len(links)})")
    if not links:
        print("(none)")
        return

    for link in links:
        print(link)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract and classify links from a web page for authorized reconnaissance."
    )
    parser.add_argument("url", help="Target page URL, e.g. https://example.com")
    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Show only links that belong to the target host.",
    )
    parser.add_argument(
        "--path-prefix",
        help=(
            "Restrict internal links to one path prefix, "
            "for example /Deeb-M/CyberScraper."
        ),
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
        links, final_url = scrape(args.url, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"[!] Request failed: {exc}")
        return 1

    internal, external = classify_links(
        links,
        final_url,
        path_prefix=args.path_prefix,
    )

    visible_total = len(internal) if args.internal_only else len(internal) + len(external)
    print(f"[+] Found {len(links)} unique link(s)")
    print(f"[+] Showing {visible_total} link(s) after filters")

    print_group("INTERNAL", internal)
    if not args.internal_only:
        print_group("EXTERNAL", external)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
