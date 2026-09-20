#!/usr/bin/env python3
"""CyberScraper - a small link discovery tool for authorized reconnaissance."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = 10
USER_AGENT = "CyberScraper/0.3 (+authorized-security-research)"


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


def build_report(
    requested_url: str,
    final_url: str,
    all_links: list[str],
    internal: list[str],
    external: list[str],
    internal_only: bool,
    path_prefix: str | None,
) -> dict:
    """Build a serializable report for JSON/CSV export."""
    visible_external = [] if internal_only else external
    return {
        "requested_url": requested_url,
        "final_url": final_url,
        "total_found": len(all_links),
        "total_shown": len(internal) + len(visible_external),
        "filters": {
            "internal_only": internal_only,
            "path_prefix": path_prefix,
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
        "--output",
        help="Save filtered results to a .json or .csv file.",
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

    if args.output:
        try:
            output_format_for_path(args.output)
        except ValueError as exc:
            print(f"[!] {exc}")
            return 2

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

    if args.output:
        report = build_report(
            requested_url=args.url,
            final_url=final_url,
            all_links=links,
            internal=internal,
            external=external,
            internal_only=args.internal_only,
            path_prefix=args.path_prefix,
        )
        output_format = save_report(args.output, report)
        print(f"\n[+] Saved {output_format.upper()} results to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
