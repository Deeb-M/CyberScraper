#!/usr/bin/env python3
"""Core crawling, filtering, analysis, and export logic for Scryx."""

from __future__ import annotations

import csv
import json
import time
from collections import deque
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

from . import __version__

DEFAULT_TIMEOUT = 10
DEFAULT_DELAY = 0.25
DEFAULT_MAX_PAGES = 25
DEFAULT_CHECK_LIMIT = 25
MAX_CRAWL_DEPTH = 2
MAX_PAGE_LIMIT = 100
MAX_CHECK_LIMIT = 50
MAX_REDIRECTS = 10
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
USER_AGENT = f"Scryx/{__version__} (+authorized-security-research)"
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}

STATIC_ASSET_EXTENSIONS = {
    ".7z",
    ".avi",
    ".bmp",
    ".css",
    ".csv",
    ".eot",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".map",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".svg",
    ".tar",
    ".tgz",
    ".ttf",
    ".txt",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xml",
    ".zip",
}


def prepare_target_url(value: str) -> str:
    """Normalize a CLI target and default a missing scheme to HTTPS."""
    target = value.strip()
    if not target:
        raise ValueError("Target URL cannot be empty")

    if "://" not in target:
        target = f"https://{target}"

    parsed = urlparse(target)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Target URL must use http:// or https://")
    if not parsed.netloc:
        raise ValueError("Target URL must include a host")

    return parsed._replace(scheme=parsed.scheme.lower()).geturl()


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
    """Extract unique normalized navigation/resource URLs from HTML.

    This intentionally parses only explicit HTML URL-bearing attributes. It
    does not execute JavaScript or guess URLs from arbitrary script text.
    """
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()

    url_attributes = {
        "a": ("href",),
        "area": ("href",),
        "form": ("action",),
        "iframe": ("src",),
        "frame": ("src",),
        "script": ("src",),
        "link": ("href",),
    }

    for tag_name, attributes in url_attributes.items():
        for tag in soup.find_all(tag_name):
            for attribute in attributes:
                value = tag.get(attribute)
                if not value:
                    continue
                normalized = normalize_url(base_url, value)
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


def query_parameters(url: str) -> list[str]:
    """Return sorted unique query-parameter names from a URL."""
    return sorted({key for key, _value in parse_qsl(urlparse(url).query, keep_blank_values=True)})


def is_static_asset(url: str) -> bool:
    """Return True when the URL path looks like a static/file asset."""
    return Path(urlparse(url).path).suffix.lower() in STATIC_ASSET_EXTENSIONS


def is_crawlable_page(url: str) -> bool:
    """Return True when a discovered URL is suitable for the HTML crawl queue."""
    return not is_static_asset(url)


def analyze_links(links: list[str]) -> dict:
    """Build deterministic URL-shape intelligence for discovered links."""
    static_assets: list[str] = []
    pages: list[str] = []
    parameterized: list[dict[str, object]] = []
    dynamic_candidates: list[str] = []
    unique_parameters: set[str] = set()

    for link in sorted(set(links)):
        params = query_parameters(link)
        static = is_static_asset(link)

        if static:
            static_assets.append(link)
        else:
            pages.append(link)

        if params:
            parameterized.append({"url": link, "parameters": params})
            unique_parameters.update(params)
            if not static:
                dynamic_candidates.append(link)

    asset_types: dict[str, int] = {}
    for asset in static_assets:
        extension = Path(urlparse(asset).path).suffix.lower() or "[no extension]"
        asset_types[extension] = asset_types.get(extension, 0) + 1

    return {
        "summary": {
            "pages": len(pages),
            "static_assets": len(static_assets),
            "parameterized": len(parameterized),
            "dynamic_candidates": len(dynamic_candidates),
            "unique_parameters": len(unique_parameters),
            "asset_types": len(asset_types),
        },
        "pages": pages,
        "static_assets": static_assets,
        "asset_types": dict(sorted(asset_types.items())),
        "parameterized": parameterized,
        "dynamic_candidates": dynamic_candidates,
        "unique_parameters": sorted(unique_parameters),
    }


def build_recon_intelligence(
    target_url: str,
    internal: list[str],
    external: list[str],
    analysis: dict,
    http_checks: list[dict] | None = None,
) -> dict:
    """Build factual, deterministic recon intelligence from collected results."""
    http_checks = http_checks or []
    target_host = urlparse(target_url).netloc.lower()
    internal_hosts = sorted({urlparse(url).netloc.lower() for url in internal if urlparse(url).netloc})
    external_hosts = sorted({urlparse(url).netloc.lower() for url in external if urlparse(url).netloc})

    parameterized_urls = [
        item["url"]
        for item in analysis.get("parameterized", [])
        if item.get("url") and is_internal_link(item["url"], target_url)
    ]
    dynamic_candidates = [
        url
        for url in analysis.get("dynamic_candidates", [])
        if is_internal_link(url, target_url)
    ]
    redirects = [item["url"] for item in http_checks if item.get("redirected")]
    broken_or_error = [
        item["url"]
        for item in http_checks
        if item.get("broken") or item.get("error")
    ]

    leads: list[dict[str, object]] = []
    if parameterized_urls:
        leads.append({
            "type": "parameterized_routes",
            "count": len(parameterized_urls),
            "items": parameterized_urls,
            "note": "Internal routes with query parameters were discovered.",
        })
    if external_hosts:
        leads.append({
            "type": "external_hosts",
            "count": len(external_hosts),
            "items": external_hosts,
            "note": "External hosts were referenced by discovered links; they were not crawled.",
        })
    if redirects:
        leads.append({
            "type": "redirects",
            "count": len(redirects),
            "items": redirects,
            "note": "Checked URLs with redirect behavior were observed.",
        })
    if broken_or_error:
        leads.append({
            "type": "http_errors",
            "count": len(broken_or_error),
            "items": broken_or_error,
            "note": "Checked URLs returned an HTTP error status or request error.",
        })

    return {
        "target_host": target_host,
        "hosts": {
            "internal": internal_hosts,
            "external": external_hosts,
            "internal_count": len(internal_hosts),
            "external_count": len(external_hosts),
        },
        "internal_parameterized_routes": parameterized_urls,
        "internal_dynamic_candidates": dynamic_candidates,
        "leads": leads,
        "scope_note": "Recon intelligence is derived only from discovered links and bounded HTTP checks; it is not a vulnerability assessment.",
    }


def _request_with_scoped_redirects(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    stream: bool = False,
    path_prefix: str | None = None,
) -> tuple[requests.Response, str, int, str | None]:
    """Follow redirects only while they remain inside the requested host/scope."""
    headers = {"User-Agent": USER_AGENT}
    scope_url = canonical_crawl_url(url)
    current_url = scope_url
    seen: set[str] = set()
    redirect_count = 0

    while True:
        key = canonical_crawl_url(current_url)
        if key in seen:
            raise requests.TooManyRedirects("redirect loop detected")
        seen.add(key)

        response = requests.get(
            current_url,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
            stream=stream,
        )

        location = response.headers.get("Location")
        if response.status_code in REDIRECT_STATUS_CODES and location:
            redirect_target = normalize_url(current_url, location)
            if redirect_target is None:
                return response, current_url, redirect_count, None

            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                response.close()
                raise requests.TooManyRedirects(
                    f"redirect limit exceeded ({MAX_REDIRECTS})"
                )

            if not is_internal_link(redirect_target, scope_url):
                return response, current_url, redirect_count, redirect_target

            if path_prefix and not path_matches_prefix(redirect_target, path_prefix):
                return response, current_url, redirect_count, redirect_target

            response.close()
            current_url = canonical_crawl_url(redirect_target)
            continue

        return response, current_url, redirect_count, None


def scrape(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    path_prefix: str | None = None,
) -> tuple[list[str], str]:
    """Fetch one page without following redirects outside the requested scope."""
    response = None

    try:
        response, final_url, _redirects, blocked_redirect = _request_with_scoped_redirects(
            url,
            timeout=timeout,
            stream=False,
            path_prefix=path_prefix,
        )

        if blocked_redirect is not None:
            raise requests.RequestException(
                f"redirect escaped scope: {blocked_redirect}"
            )

        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type and media_type not in HTML_CONTENT_TYPES:
            return [], final_url

        return extract_links(response.text, final_url), final_url
    finally:
        if response is not None:
            response.close()


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

    External links are collected but never intentionally queued. Secondary
    responses that finish outside the established host/path scope are ignored.
    """
    start_url = canonical_crawl_url(url)
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    queued: set[str] = {start_url}
    visited: set[str] = set()
    resolved: set[str] = set()
    discovered: set[str] = set()
    errors: list[tuple[str, str]] = []
    first_final_url: str | None = None
    request_attempts = 0

    while queue and len(visited) < max_pages:
        current_url, current_depth = queue.popleft()
        queued.discard(current_url)
        if current_url in visited or current_url in resolved:
            continue

        visited.add(current_url)

        if request_attempts > 0 and delay > 0:
            time.sleep(delay)
        request_attempts += 1

        try:
            links, final_url = scrape(
                current_url,
                timeout=timeout,
                path_prefix=path_prefix,
            )
        except requests.RequestException as exc:
            if current_url == start_url and first_final_url is None:
                raise
            errors.append((current_url, str(exc)))
            continue

        final_url = canonical_crawl_url(final_url)
        resolved.add(final_url)

        if first_final_url is None:
            first_final_url = final_url
        else:
            if not is_internal_link(final_url, first_final_url):
                errors.append(
                    (current_url, f"redirect escaped host scope: {final_url}")
                )
                continue
            if path_prefix and not path_matches_prefix(final_url, path_prefix):
                errors.append(
                    (current_url, f"redirect escaped path scope: {final_url}")
                )
                continue

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
            if not is_crawlable_page(link):
                continue

            crawl_link = canonical_crawl_url(link)
            if (
                crawl_link not in visited
                and crawl_link not in resolved
                and crawl_link not in queued
            ):
                queue.append((crawl_link, current_depth + 1))
                queued.add(crawl_link)

    return sorted(discovered), first_final_url or start_url, sorted(visited), errors


def check_http_status(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Perform a lightweight GET while preventing cross-host redirect escape."""
    response = None

    try:
        response, final_url, redirect_count, blocked_redirect = (
            _request_with_scoped_redirects(
                url,
                timeout=timeout,
                stream=True,
            )
        )
        return {
            "url": url,
            "status": response.status_code,
            "final_url": final_url,
            "redirected": redirect_count > 0,
            "blocked_redirect": blocked_redirect,
            "broken": response.status_code >= 400,
            "error": None,
        }
    except requests.RequestException as exc:
        return {
            "url": url,
            "status": None,
            "final_url": None,
            "redirected": False,
            "blocked_redirect": None,
            "broken": True,
            "error": str(exc),
        }
    finally:
        if response is not None:
            response.close()


def check_http_links(
    urls: list[str],
    timeout: int = DEFAULT_TIMEOUT,
    limit: int = DEFAULT_CHECK_LIMIT,
    delay: float = DEFAULT_DELAY,
) -> list[dict]:
    """Check a bounded, deduplicated list of URLs."""
    selected: list[str] = []
    seen: set[str] = set()

    for url in urls:
        key = canonical_crawl_url(url)
        if key in seen:
            continue
        seen.add(key)
        selected.append(url)
        if len(selected) >= limit:
            break

    results: list[dict] = []
    for index, url in enumerate(selected):
        results.append(check_http_status(url, timeout=timeout))
        if delay > 0 and index < len(selected) - 1:
            time.sleep(delay)

    return results


def summarize_http_checks(checks: list[dict]) -> dict:
    """Summarize bounded HTTP checks."""
    return {
        "checked": len(checks),
        "redirects": sum(1 for item in checks if item["redirected"]),
        "broken": sum(1 for item in checks if item["broken"]),
        "errors": sum(1 for item in checks if item["error"]),
        "blocked_redirects": sum(
            1 for item in checks if item.get("blocked_redirect")
        ),
    }


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
    analysis: dict | None = None,
    http_checks: list[dict] | None = None,
    preset: str | None = None,
) -> dict:
    """Build a serializable report for JSON/CSV export."""
    visible_external = [] if internal_only else external
    crawl_errors = crawl_errors or []
    analysis = analysis or analyze_links(all_links)
    http_checks = http_checks or []
    recon_intelligence = build_recon_intelligence(
        final_url,
        internal,
        external,
        analysis,
        http_checks,
    )

    return {
        "requested_url": requested_url,
        "final_url": final_url,
        "preset": preset,
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
        "analysis": analysis,
        "recon_intelligence": recon_intelligence,
        "http_checks": {
            "summary": summarize_http_checks(http_checks),
            "results": http_checks,
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
