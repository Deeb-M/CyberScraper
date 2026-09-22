"""Professional report rendering and scan-bundle output for Scryx."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


REPORT_FIELDS = [
    "category",
    "url",
    "url_type",
    "parameters",
    "status",
    "final_url",
    "redirected",
    "blocked_redirect",
    "broken",
    "error",
]


def output_format_for_path(path: str | Path) -> str:
    """Infer a supported report format from a filename."""
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".csv":
        return "csv"
    if suffix == ".txt":
        return "txt"
    raise ValueError("Output file must end with .json, .csv, or .txt")


def _http_check_map(report: dict) -> dict[str, dict]:
    return {
        item["url"]: item
        for item in report.get("http_checks", {}).get("results", [])
        if item.get("url")
    }


def build_csv_rows(report: dict) -> list[dict]:
    """Build enriched link rows for CSV output."""
    checks = _http_check_map(report)
    analysis = report.get("analysis", {})
    static_assets = set(analysis.get("static_assets", []))
    parameter_map = {
        item["url"]: item.get("parameters", [])
        for item in analysis.get("parameterized", [])
        if item.get("url")
    }

    rows: list[dict] = []
    links = report.get("links", {})

    for category in ("internal", "external"):
        for url in links.get(category, []):
            check = checks.get(url, {})
            rows.append(
                {
                    "category": category.upper(),
                    "url": url,
                    "url_type": "STATIC" if url in static_assets else "PAGE",
                    "parameters": ",".join(parameter_map.get(url, [])),
                    "status": "" if check.get("status") is None else check.get("status"),
                    "final_url": check.get("final_url") or "",
                    "redirected": bool(check.get("redirected", False)),
                    "blocked_redirect": check.get("blocked_redirect") or "",
                    "broken": bool(check.get("broken", False)),
                    "error": check.get("error") or "",
                }
            )

    return rows


def render_text_report(report: dict) -> str:
    """Render a concise human-readable report."""
    crawl = report.get("crawl", {})
    analysis = report.get("analysis", {}).get("summary", {})
    http = report.get("http_checks", {}).get("summary", {})
    intelligence = report.get("recon_intelligence", {})
    hosts = intelligence.get("hosts", {})
    preset = report.get("preset") or "custom"

    lines = [
        "Scryx Recon Report",
        "==================",
        f"Target: {report.get('requested_url', '')}",
        f"Final URL: {report.get('final_url', '')}",
        f"Preset: {preset}",
        "",
        "Discovery",
        "---------",
        f"Links found: {report.get('total_found', 0)}",
        f"Links shown: {report.get('total_shown', 0)}",
        f"Internal links: {len(report.get('links', {}).get('internal', []))}",
        f"External links: {len(report.get('links', {}).get('external', []))}",
        "",
        "Crawl",
        "-----",
        f"Depth: {crawl.get('depth', 0)}",
        f"Pages attempted: {crawl.get('pages_attempted', 0)}",
        f"Pages scanned: {crawl.get('pages_scanned', 0)}",
        f"Failed requests: {crawl.get('failed_requests', 0)}",
        "",
        "URL Analysis",
        "------------",
        f"Pages/routes: {analysis.get('pages', 0)}",
        f"Static assets/files: {analysis.get('static_assets', 0)}",
        f"Parameterized URLs: {analysis.get('parameterized', 0)}",
        f"Dynamic candidates: {analysis.get('dynamic_candidates', 0)}",
        f"Unique parameters: {analysis.get('unique_parameters', 0)}",
        "",
        "Recon Intelligence",
        "------------------",
        f"Target host: {intelligence.get('target_host', '')}",
        f"Internal hosts observed: {hosts.get('internal_count', 0)}",
        f"External hosts referenced: {hosts.get('external_count', 0)}",
        f"Internal parameterized routes: {len(intelligence.get('internal_parameterized_routes', []))}",
        f"Internal dynamic candidates: {len(intelligence.get('internal_dynamic_candidates', []))}",
        "",
        "HTTP Checks",
        "-----------",
        f"Checked: {http.get('checked', 0)}",
        f"Redirects: {http.get('redirects', 0)}",
        f"Blocked redirects: {http.get('blocked_redirects', 0)}",
        f"Broken/error results: {http.get('broken', 0)}",
        f"Request errors: {http.get('errors', 0)}",
    ]

    asset_types = report.get("analysis", {}).get("asset_types", {})
    if asset_types:
        resource_summary = ", ".join(
            f"{extension}: {count}"
            for extension, count in asset_types.items()
        )
        url_analysis_index = lines.index("Recon Intelligence")
        lines.insert(url_analysis_index - 1, f"Resource types: {resource_summary}")

    leads = intelligence.get("leads", [])
    if leads:
        lines.extend(["", "Recon Leads", "-----------"])
        for lead in leads:
            lines.append(f"{lead.get('type', 'lead')}: {lead.get('count', 0)}")
            if lead.get("note"):
                lines.append(f"  {lead['note']}")

    unique_parameters = report.get("analysis", {}).get("unique_parameters", [])
    if unique_parameters:
        lines.extend(["", "Parameters", "----------", ", ".join(unique_parameters)])

    interesting = [
        item
        for item in report.get("http_checks", {}).get("results", [])
        if (
            item.get("redirected")
            or item.get("blocked_redirect")
            or item.get("broken")
            or item.get("error")
        )
    ]
    if interesting:
        lines.extend(["", "HTTP Findings", "-------------"])
        for item in interesting:
            status = item.get("status")
            label = "ERR" if status is None else str(status)
            if item.get("blocked_redirect"):
                suffix = f" - blocked redirect -> {item.get('blocked_redirect')}"
            elif item.get("redirected"):
                suffix = f" -> {item.get('final_url')}"
            else:
                suffix = ""
            error = f" | {item.get('error')}" if item.get("error") else ""
            lines.append(f"[{label}] {item.get('url')}{suffix}{error}")

    return "\n".join(lines) + "\n"


def save_report(path: str | Path, report: dict) -> str:
    """Save one report as JSON, enriched CSV, or text."""
    output_path = Path(path)
    output_format = output_format_for_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "json":
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif output_format == "txt":
        output_path.write_text(render_text_report(report), encoding="utf-8")
    else:
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            writer.writerows(build_csv_rows(report))

    return output_format


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._")
    return cleaned or "scan"


def build_scan_directory_name(
    report: dict,
    timestamp: datetime | None = None,
) -> str:
    """Build a sortable directory name for one scan."""
    timestamp = timestamp or datetime.now(timezone.utc)
    stamp = timestamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    host = urlparse(report.get("requested_url", "")).netloc or "target"
    preset = report.get("preset") or "custom"
    return f"{stamp}_{_slug(host)}_{_slug(preset)}"


def save_scan_bundle(
    base_dir: str | Path,
    report: dict,
    timestamp: datetime | None = None,
) -> Path:
    """Create a scan directory containing JSON, CSV, and TXT reports."""
    root = Path(base_dir)
    base_name = build_scan_directory_name(report, timestamp=timestamp)
    suffix = 1

    while True:
        directory_name = base_name if suffix == 1 else f"{base_name}_{suffix}"
        scan_dir = root / directory_name
        try:
            scan_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            suffix += 1

    save_report(scan_dir / "report.json", report)
    save_report(scan_dir / "links.csv", report)
    save_report(scan_dir / "summary.txt", report)

    return scan_dir
