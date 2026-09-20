"""Command-line interface for Scryx."""

from __future__ import annotations

import argparse

import requests

from . import __version__
from .core import (
    DEFAULT_DELAY,
    DEFAULT_MAX_PAGES,
    DEFAULT_TIMEOUT,
    MAX_CRAWL_DEPTH,
    MAX_PAGE_LIMIT,
    build_report,
    classify_links,
    crawl,
    normalize_extensions,
    output_format_for_path,
    print_crawl_errors,
    print_group,
    save_report,
    scrape,
)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scryx - focused web reconnaissance for authorized security work."
    )
    parser.add_argument("url", nargs="?", help="Target page URL, e.g. https://example.com")\n    parser.add_argument("--version", action="version", version=f"Scryx {__version__}")
    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Show only links that belong to the target host.",
    )
    parser.add_argument(
        "--path-prefix",
        help=(
            "Restrict internal links and crawl scope to one path prefix, "
            "for example /Deeb-M/CyberScraper."
        ),
    )
    parser.add_argument(
        "--exclude-path-prefix",
        action="append",
        default=[],
        help=(
            "Exclude an internal path prefix from output and crawling. "
            "Repeat the option to exclude multiple prefixes."
        ),
    )
    parser.add_argument(
        "--exclude-extension",
        action="append",
        default=[],
        help=(
            "Exclude links ending with a file extension, for example pdf or .zip. "
            "Repeat the option to exclude multiple extensions."
        ),
    )
    parser.add_argument(
        "--depth",
        type=int,
        choices=range(0, MAX_CRAWL_DEPTH + 1),
        default=0,
        metavar="0|1|2",
        help="Crawl depth. 0 scans one page; maximum is 2 (default: 0).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"Maximum pages to request during crawling (default: {DEFAULT_MAX_PAGES}, max: {MAX_PAGE_LIMIT}).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Delay in seconds between crawl requests (default: {DEFAULT_DELAY}).",
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

    if not 1 <= args.max_pages <= MAX_PAGE_LIMIT:
        print(f"[!] --max-pages must be between 1 and {MAX_PAGE_LIMIT}")
        return 2
    if args.delay < 0:
        print("[!] --delay cannot be negative")
        return 2
    if args.output:
        try:
            output_format_for_path(args.output)
        except ValueError as exc:
            print(f"[!] {exc}")
            return 2

    excluded_extensions = normalize_extensions(args.exclude_extension)

    try:
        if args.depth == 0:
            links, final_url = scrape(args.url, timeout=args.timeout)
            pages_scanned = [final_url]
            crawl_errors: list[tuple[str, str]] = []
        else:
            links, final_url, pages_scanned, crawl_errors = crawl(
                args.url,
                depth=args.depth,
                max_pages=args.max_pages,
                timeout=args.timeout,
                path_prefix=args.path_prefix,
                exclude_path_prefixes=args.exclude_path_prefix,
                exclude_extensions=excluded_extensions,
                delay=args.delay,
            )
    except requests.RequestException as exc:
        print(f"[!] Request failed: {exc}")
        return 1

    internal, external = classify_links(
        links,
        final_url,
        path_prefix=args.path_prefix,
        exclude_path_prefixes=args.exclude_path_prefix,
        exclude_extensions=excluded_extensions,
    )

    visible_total = len(internal) if args.internal_only else len(internal) + len(external)
    attempted_pages = len(pages_scanned)
    successful_pages = attempted_pages - len(crawl_errors)

    print(f"[+] Attempted {attempted_pages} page(s)")
    print(f"[+] Successfully scanned {successful_pages} page(s)")
    print(f"[+] Found {len(links)} unique link(s)")
    print(f"[+] Showing {visible_total} link(s) after filters")

    print_crawl_errors(crawl_errors)

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
            exclude_path_prefixes=args.exclude_path_prefix,
            exclude_extensions=excluded_extensions,
            depth=args.depth,
            pages_scanned=len(pages_scanned),
            max_pages=args.max_pages,
            crawl_errors=crawl_errors,
        )
        output_format = save_report(args.output, report)
        print(f"\n[+] Saved {output_format.upper()} results to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
