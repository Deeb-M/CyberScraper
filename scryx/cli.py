"""Command-line interface for Scryx."""

from __future__ import annotations

import argparse

import requests

from . import __version__
from .core import (
    DEFAULT_CHECK_LIMIT,
    DEFAULT_DELAY,
    DEFAULT_MAX_PAGES,
    DEFAULT_TIMEOUT,
    MAX_CHECK_LIMIT,
    MAX_CRAWL_DEPTH,
    MAX_PAGE_LIMIT,
    analyze_links,
    build_report,
    check_http_links,
    classify_links,
    crawl,
    normalize_extensions,
    prepare_target_url,
    print_crawl_errors,
    print_group,
    scrape,
    summarize_http_checks,
)
from .reporting import output_format_for_path, save_report, save_scan_bundle

PRESETS = {
    "quick": {
        "depth": 0,
        "max_pages": 10,
        "delay": 0.25,
        "check_links": False,
        "check_limit": 10,
    },
    "recon": {
        "depth": 1,
        "max_pages": 25,
        "delay": 0.35,
        "check_links": True,
        "check_limit": 25,
    },
    "deep": {
        "depth": 2,
        "max_pages": 75,
        "delay": 0.50,
        "check_links": True,
        "check_limit": 50,
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scryx",
        description="Scryx - focused web reconnaissance for authorized security work.",
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Target page URL or host. Missing schemes default to https://.",
    )
    parser.add_argument("--version", action="version", version=f"Scryx {__version__}")

    preset_group = parser.add_mutually_exclusive_group()
    preset_group.add_argument(
        "--quick",
        action="store_true",
        help="One-page discovery with lightweight defaults and no extra link checks.",
    )
    preset_group.add_argument(
        "--recon",
        action="store_true",
        help="Balanced same-host crawl plus bounded HTTP status/redirect checks.",
    )
    preset_group.add_argument(
        "--deep",
        action="store_true",
        help="Deeper bounded crawl and larger same-host HTTP check budget.",
    )

    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Show only links that belong to the target host.",
    )
    parser.add_argument(
        "--path-prefix",
        help="Restrict internal links and crawl scope to one path prefix.",
    )
    parser.add_argument(
        "--exclude-path-prefix",
        action="append",
        default=[],
        help="Exclude an internal path prefix. Repeat to exclude multiple prefixes.",
    )
    parser.add_argument(
        "--exclude-extension",
        action="append",
        default=[],
        help="Exclude a file extension such as pdf or .zip. Repeat as needed.",
    )
    parser.add_argument(
        "--depth",
        type=int,
        choices=range(0, MAX_CRAWL_DEPTH + 1),
        default=None,
        metavar="0|1|2",
        help="Override crawl depth. Maximum is 2.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help=f"Override maximum crawl requests (hard max: {MAX_PAGE_LIMIT}).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Override delay in seconds between crawl/check requests.",
    )
    parser.add_argument(
        "--check-links",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable bounded HTTP status/redirect checks.",
    )
    parser.add_argument(
        "--check-external",
        action="store_true",
        help="Also check discovered external links. External hosts are never crawled.",
    )
    parser.add_argument(
        "--check-limit",
        type=int,
        default=None,
        help=f"Maximum URLs to status-check (hard max: {MAX_CHECK_LIMIT}).",
    )
    parser.add_argument(
        "--output",
        help="Save one report to .json, .csv, or .txt.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Create a timestamped scan directory with JSON, CSV, and TXT reports.",
    )
    parser.add_argument(
        "--report-dir",
        help="Base directory for scan bundles (implies --report).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    return parser


def selected_preset(args: argparse.Namespace) -> str | None:
    for name in ("quick", "recon", "deep"):
        if getattr(args, name):
            return name
    return None


def resolve_scan_settings(args: argparse.Namespace) -> dict:
    """Resolve preset values, then apply explicit command-line overrides."""
    preset = selected_preset(args)
    base = {
        "depth": 0,
        "max_pages": DEFAULT_MAX_PAGES,
        "delay": DEFAULT_DELAY,
        "check_links": False,
        "check_limit": DEFAULT_CHECK_LIMIT,
    }

    if preset:
        base.update(PRESETS[preset])

    if args.depth is not None:
        base["depth"] = args.depth
    if args.max_pages is not None:
        base["max_pages"] = args.max_pages
    if args.delay is not None:
        base["delay"] = args.delay
    if args.check_links is not None:
        base["check_links"] = args.check_links
    if args.check_limit is not None:
        base["check_limit"] = args.check_limit

    base["preset"] = preset
    return base


def print_url_analysis(analysis: dict) -> None:
    summary = analysis["summary"]
    print("\n[URL ANALYSIS]")
    print(f"Pages/routes: {summary['pages']}")
    print(f"Static assets/files: {summary['static_assets']}")
    print(f"Parameterized URLs: {summary['parameterized']}")
    print(f"Dynamic candidates: {summary['dynamic_candidates']}")
    print(f"Unique parameters: {summary['unique_parameters']}")

    if analysis["unique_parameters"]:
        print("Parameters: " + ", ".join(analysis["unique_parameters"]))


def print_http_checks(checks: list[dict]) -> None:
    if not checks:
        return

    summary = summarize_http_checks(checks)
    print(f"\n[HTTP CHECKS] ({summary['checked']})")

    for item in checks:
        if item["error"]:
            print(f"[ERR] {item['url']} - {item['error']}")
            continue

        suffix = ""
        if item.get("blocked_redirect"):
            suffix = f" - blocked redirect -> {item['blocked_redirect']}"
        elif item["redirected"]:
            suffix = f" -> {item['final_url']}"
        print(f"[{item['status']}] {item['url']}{suffix}")

    print(
        "[+] HTTP summary: "
        f"{summary['redirects']} redirect(s), "
        f"{summary['blocked_redirects']} blocked redirect(s), "
        f"{summary['broken']} broken/error result(s)"
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.url:
        parser.print_help()
        return 2

    try:
        target_url = prepare_target_url(args.url)
    except ValueError as exc:
        print(f"[!] {exc}")
        return 2

    settings = resolve_scan_settings(args)

    if not 1 <= settings["max_pages"] <= MAX_PAGE_LIMIT:
        print(f"[!] --max-pages must be between 1 and {MAX_PAGE_LIMIT}")
        return 2
    if settings["delay"] < 0:
        print("[!] --delay cannot be negative")
        return 2
    if not 1 <= settings["check_limit"] <= MAX_CHECK_LIMIT:
        print(f"[!] --check-limit must be between 1 and {MAX_CHECK_LIMIT}")
        return 2
    if args.timeout <= 0:
        print("[!] --timeout must be greater than 0")
        return 2
    if args.output:
        try:
            output_format_for_path(args.output)
        except ValueError as exc:
            print(f"[!] {exc}")
            return 2

    excluded_extensions = normalize_extensions(args.exclude_extension)

    try:
        if settings["depth"] == 0:
            links, final_url = scrape(
                target_url,
                timeout=args.timeout,
                path_prefix=args.path_prefix,
            )
            pages_scanned = [final_url]
            crawl_errors: list[tuple[str, str]] = []
        else:
            links, final_url, pages_scanned, crawl_errors = crawl(
                target_url,
                depth=settings["depth"],
                max_pages=settings["max_pages"],
                timeout=args.timeout,
                path_prefix=args.path_prefix,
                exclude_path_prefixes=args.exclude_path_prefix,
                exclude_extensions=excluded_extensions,
                delay=settings["delay"],
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

    print(f"[+] Target: {target_url}")
    if settings["preset"]:
        print(f"[+] Preset: {settings['preset']}")
    print(f"[+] Attempted {attempted_pages} page(s)")
    print(f"[+] Successfully scanned {successful_pages} page(s)")
    print(f"[+] Found {len(links)} unique link(s)")
    print(f"[+] Showing {visible_total} link(s) after filters")

    print_crawl_errors(crawl_errors)
    print_group("INTERNAL", internal)
    if not args.internal_only:
        print_group("EXTERNAL", external)

    analysis = analyze_links(links)
    print_url_analysis(analysis)

    http_checks: list[dict] = []
    if settings["check_links"]:
        check_targets = [final_url, *internal]
        if args.check_external:
            check_targets.extend(external)
        http_checks = check_http_links(
            check_targets,
            timeout=args.timeout,
            limit=settings["check_limit"],
            delay=settings["delay"],
        )
        print_http_checks(http_checks)

    report_requested = bool(args.output or args.report or args.report_dir)
    report: dict | None = None

    if report_requested:
        report = build_report(
            requested_url=target_url,
            final_url=final_url,
            all_links=links,
            internal=internal,
            external=external,
            internal_only=args.internal_only,
            path_prefix=args.path_prefix,
            exclude_path_prefixes=args.exclude_path_prefix,
            exclude_extensions=excluded_extensions,
            depth=settings["depth"],
            pages_scanned=len(pages_scanned),
            max_pages=settings["max_pages"],
            crawl_errors=crawl_errors,
            analysis=analysis,
            http_checks=http_checks,
            preset=settings["preset"],
        )

    if args.output and report is not None:
        try:
            output_format = save_report(args.output, report)
        except OSError as exc:
            print(f"[!] Could not save report: {exc}")
            return 1
        print(f"\n[+] Saved {output_format.upper()} results to {args.output}")

    if (args.report or args.report_dir) and report is not None:
        base_dir = args.report_dir or "scryx-scans"
        try:
            scan_dir = save_scan_bundle(base_dir, report)
        except OSError as exc:
            print(f"[!] Could not save scan bundle: {exc}")
            return 1
        print(f"\n[+] Saved scan bundle to {scan_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
