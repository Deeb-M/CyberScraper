# Changelog

## 1.0.1

Small usability patch for report bundles.

- Prints the exact generated paths for `report.json`, `links.csv`, and `summary.txt` after `--report` or `--report-dir`.
- Adds CLI regression coverage for the generated-file path output.
- No crawling, scope, HTTP-check, or report-content behavior changes.

## 1.0.0

First stable Scryx release.

- Promotes the validated 1.0.0rc1 codebase to stable without changing recon behavior.
- Kali/Linux installation and global CLI usage validated through `pipx`.
- Quick, recon, and deep presets validated with bounded crawl and HTTP-check limits.
- JSON, CSV, TXT, and timestamped scan-bundle reporting validated.
- Redirect, scope, pacing, non-HTML handling, duplicate crawl, filesystem, and report-directory edge cases hardened.
- CI validated on Python 3.10, 3.12, 3.13, and 3.14.

## 1.0.0rc1

Release candidate for the first stable Scryx CLI release.

### Highlights

- Installable Kali/Linux CLI via `pipx`
- Short global `scryx` command
- Quick, recon, and deep presets
- Same-host bounded crawling with conservative depth/page limits
- URL normalization, deduplication, scope controls, exclusions, and URL-shape analysis
- Bounded HTTP status checks with redirect reporting and cross-host redirect blocking
- Non-HTML response handling and crawl pacing hardening
- JSON, enriched CSV, and TXT reports
- Timestamped scan bundles with collision-safe directories
- Clean filesystem error reporting
- CI coverage on Python 3.10, 3.12, 3.13, and 3.14

### Pre-release validation

The release-candidate workflow has been validated on Kali Linux with Python 3.14.6, including installation through `pipx`, deep scanning, HTTP checks, JSON output, and scan-bundle generation.

## 0.9.x

Hardening series covering redirects, duplicate crawl behavior, HTTP/content edge cases, pacing, reporting, and filesystem handling.

## 0.9.0

Professional reporting and scan bundles.

## 0.8.0

Integrated recon presets and bounded HTTP checking.

## 0.7.0

Installable CLI/package foundation.
