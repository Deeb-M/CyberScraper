# Scryx User Guide

This guide explains how to use Scryx in normal authorized reconnaissance workflows. The stable release is v1.1.1 and includes Recon Intelligence, broader explicit HTML URL discovery, route-level Recon Map output, and terminal color highlighting.

> Use Scryx only on systems you own or where you have explicit permission to perform reconnaissance or security testing.

## 1. Install Scryx

The simplest Kali/Linux installation from the public GitHub repository is:

```bash
pipx install git+https://github.com/Deeb-M/Scryx.git@v1.1.1
```

If Scryx is already installed and you want to reinstall the current stable release:

```bash
pipx install --force git+https://github.com/Deeb-M/Scryx.git@v1.1.1
```

Verify the installation:

```bash
scryx --version
scryx --help
```

Expected stable version:

```text
Scryx 1.1.1
```

## 2. Basic syntax

```bash
scryx TARGET [OPTIONS]
```

The target may be a hostname or a full URL.

```bash
scryx example.com --recon
scryx https://example.com --recon
```

If no scheme is supplied, Scryx defaults to HTTPS.

## 3. Recommended workflow

For most users, start with `--quick`, then use `--recon` if you need more coverage. Use `--deep` only when additional crawl depth is useful.

### Quick

```bash
scryx example.com --quick
```

Use this for a fast first look.

Defaults:

- crawl depth: 0
- maximum crawl requests: 10
- delay: 0.25 seconds
- HTTP link checks: disabled
- HTTP check limit if manually enabled: 10

Quick scans only the starting page and reports links discovered there.

### Recon

```bash
scryx example.com --recon
```

Use this as the normal balanced reconnaissance mode.

Defaults:

- crawl depth: 1
- maximum crawl requests: 25
- delay: 0.35 seconds
- HTTP link checks: enabled
- HTTP check limit: 25

### Deep

```bash
scryx example.com --deep
```

Use this when the target has additional same-host pages that may only appear one level deeper.

Defaults:

- crawl depth: 2
- maximum crawl requests: 75
- delay: 0.50 seconds
- HTTP link checks: enabled
- HTTP check limit: 50

The hard limits remain:

- maximum crawl depth: 2
- maximum crawl requests: 100
- maximum HTTP checks: 50

A deep scan does not guarantee more results. On small sites, `--recon` and `--deep` may discover exactly the same pages.

## 4. Understanding the output

A normal scan can contain the following sections.

### Target and preset

```text
[+] Target: https://example.com
[+] Preset: recon
```

This shows the normalized target and selected preset.

### Crawl summary

```text
[+] Attempted 6 page(s)
[+] Successfully scanned 6 page(s)
[+] Found 11 unique link(s)
[+] Showing 11 link(s) after filters
```

- **Attempted**: pages Scryx tried to fetch during the crawl.
- **Successfully scanned**: crawl requests that completed without recorded crawl errors.
- **Found**: unique discovered links before display filtering.
- **Showing**: links displayed after options such as `--internal-only`.

### Internal links

```text
[INTERNAL]
```

These belong to the target host and may be included in the bounded crawl.

### External links

```text
[EXTERNAL]
```

These point to other hosts.

External hosts are never added to the crawl queue.

### URL analysis

```text
[URL ANALYSIS]
Pages/routes: ...
Static assets/files: ...
Parameterized URLs: ...
Dynamic candidates: ...
Unique parameters: ...
```

Scryx uses deterministic URL-shape heuristics:

- **Page/route**: URL not classified as a static asset.
- **Static asset/file**: path ends in a recognized file/asset extension.
- **Parameterized URL**: contains query parameters.
- **Dynamic candidate**: parameterized URL that is not classified as a static asset.
- **Unique parameters**: unique query-parameter names discovered in URLs.

A dynamic candidate is only a reconnaissance hint. It does not prove that server-side dynamic code is vulnerable or even that the parameter affects application behavior.

`--internal-only` controls which link groups are displayed, but URL analysis is calculated from all discovered links. Therefore an external URL can still contribute a parameter name to the URL-analysis summary.

### Recon Intelligence (v1.1.1)

After URL analysis, Scryx can summarize observed hosts, internal parameterized routes, dynamic candidates, factual recon leads, and suggested next steps.

The suggested next steps are deterministic workflow guidance based only on what the scan observed. They do not label routes, parameters, redirects, resources, or HTTP errors as vulnerabilities.

Scryx also discovers explicit URLs from HTML attributes on `a`, `area`, `form`, `iframe`, `frame`, `script`, and `link` elements. Static resources such as JavaScript and CSS remain visible in discovery and analysis, but are not placed in the HTML crawl queue.

Scryx still does not execute JavaScript or guess URLs from arbitrary inline script text.

### HTTP checks

When enabled, Scryx prints bounded status and redirect checks:

```text
[HTTP CHECKS]
[200] https://example.com/
```

The summary reports redirects, blocked redirects, and broken/error results.

## 5. Scope and filtering options

### Show only internal links

```bash
scryx example.com --recon --internal-only
```

This hides external links from the displayed link groups.

It does not change the URL-analysis data set; URL analysis still uses all discovered links.

### Restrict the crawl to one path prefix

```bash
scryx example.com/project --recon --path-prefix /project
```

Use this when your authorization or test scope is limited to one part of a site.

Redirects that escape the requested path scope are blocked.

### Exclude path prefixes

```bash
scryx example.com --recon \
  --exclude-path-prefix /archive \
  --exclude-path-prefix /login
```

The option may be repeated.

### Exclude file extensions

```bash
scryx example.com --recon \
  --exclude-extension pdf \
  --exclude-extension .zip
```

Both `pdf` and `.pdf` style inputs are accepted after normalization.

The option may be repeated.

## 6. Manual crawl controls

Presets are recommended for normal use, but their values can be overridden.

### Crawl depth

```bash
scryx example.com --depth 1
```

Allowed values:

```text
0
1
2
```

Maximum: 2.

### Maximum crawl requests

```bash
scryx example.com --depth 1 --max-pages 15
```

Allowed range:

```text
1-100
```

### Delay between requests

```bash
scryx example.com --recon --delay 0.75
```

The value is in seconds.

Use conservative delays and respect the target's rules, infrastructure, and authorized scope.

### Timeout

```bash
scryx example.com --recon --timeout 15
```

The value is in seconds.

Default:

```text
10
```

The timeout must be greater than zero.

## 7. HTTP-check controls

### Enable HTTP checks

```bash
scryx example.com --check-links
```

### Disable HTTP checks

```bash
scryx example.com --recon --no-check-links
```

This is useful when you want discovery without the additional status-check pass.

### Set the check limit

```bash
scryx example.com --recon --check-limit 20
```

Allowed range:

```text
1-50
```

### Check external links

```bash
scryx example.com --recon --check-external
```

By default, external links are discovered and reported but are not status-checked.

`--check-external` sends HTTP requests to discovered external hosts. Use it only when those external requests are permitted by your authorization and scope.

External hosts are never crawled, even when `--check-external` is used.

## 8. Redirect behavior

Scryx deliberately keeps redirects inside the requested scope.

If a target such as:

```text
https://example.com
```

redirects to a different host such as:

```text
https://www.example.com/
```

Scryx may report:

```text
[!] Request failed: redirect escaped scope
```

This is intentional. The `www` host and the apex host are different network locations for Scryx scope enforcement.

If both hosts are authorized, run Scryx directly against the final authorized host:

```bash
scryx www.example.com --recon
```

Do not interpret a redirect-scope block as a vulnerability.

## 9. Reports and saved output

### Save one report

JSON:

```bash
scryx example.com --recon --output results.json
```

CSV:

```bash
scryx example.com --recon --output results.csv
```

TXT:

```bash
scryx example.com --recon --output summary.txt
```

The file extension selects the output format.

### Create a complete report bundle

```bash
scryx example.com --recon --report
```

By default, Scryx creates a timestamped directory under:

```text
scryx-scans/
```

Each bundle contains:

```text
report.json
links.csv
summary.txt
```

After saving a bundle, Scryx prints the exact path to the scan directory and the exact path to each of these three files, so you can copy a path directly into commands such as `cat`, `less`, or another analysis tool.

### Choose another report directory

```bash
scryx example.com --recon --report-dir ~/recon-reports
```

`--report-dir` implies `--report`.

## 10. Terminal colors

Scryx uses a restrained color hierarchy to make important reconnaissance information easier to identify without turning normal output into visual noise.

- **Orange**: section headings.
- **Cyan**: selected recon-relevant structure and findings, such as parameterized routes and parameters.
- **Yellow**: redirects and items that deserve review.
- **Red**: HTTP errors and failures.
- Normal informational output and routine successful HTTP 2xx checks remain unaccented.

Color behavior can be controlled with:

```bash
scryx example.com --recon --color auto
scryx example.com --recon --color always
scryx example.com --recon --color never
```

`auto` is the default and enables colors when output is connected to a terminal.

## 11. Full option reference

The authoritative current option list is always available from:

```bash
scryx --help
```

| Option | Purpose |
| --- | --- |
| `-h, --help` | Show command help. |
| `--version` | Show the installed Scryx version. |
| `--quick` | One-page lightweight discovery; no extra link checks by default. |
| `--recon` | Balanced same-host crawl with bounded HTTP checks. |
| `--deep` | Deeper bounded crawl with the largest built-in check budget. |
| `--internal-only` | Display only links belonging to the target host. |
| `--path-prefix PATH_PREFIX` | Restrict internal links and crawl scope to one path prefix. |
| `--exclude-path-prefix PATH` | Exclude one internal path prefix; repeat as needed. |
| `--exclude-extension EXT` | Exclude a file extension; repeat as needed. |
| `--depth 0|1|2` | Override crawl depth. |
| `--max-pages N` | Override maximum crawl requests; hard maximum 100. |
| `--delay SECONDS` | Override delay between crawl/check requests. |
| `--check-links` | Enable bounded HTTP status/redirect checks. |
| `--no-check-links` | Disable bounded HTTP status/redirect checks. |
| `--check-external` | Also status-check discovered external links; never crawl them. |
| `--check-limit N` | Maximum URLs to status-check; hard maximum 50. |
| `--output FILE` | Save one JSON, CSV, or TXT report. |
| `--report` | Create a timestamped JSON/CSV/TXT scan bundle. |
| `--report-dir DIR` | Set the base directory for report bundles and imply `--report`. |
| `--color auto|always|never` | Control terminal color output; default `auto`. |
| `--timeout SECONDS` | Set HTTP timeout; default 10 seconds. |

The preset options `--quick`, `--recon`, and `--deep` are mutually exclusive.

## 12. Practical examples

Fast first look:

```bash
scryx example.com --quick
```

Normal reconnaissance with a report bundle:

```bash
scryx example.com --recon --report
```

Deeper same-host crawl:

```bash
scryx example.com --deep --report
```

Authorized path-only assessment:

```bash
scryx example.com/app --recon --path-prefix /app --report
```

Internal links only:

```bash
scryx example.com --recon --internal-only
```

Exclude archives and downloadable files:

```bash
scryx example.com --recon \
  --exclude-path-prefix /archive \
  --exclude-extension pdf \
  --exclude-extension zip
```

Custom bounded scan:

```bash
scryx example.com --depth 1 --max-pages 20 --delay 0.75 --check-links --check-limit 20
```

## 13. What Scryx does not do

Scryx is a bounded web reconnaissance tool. It is not a vulnerability scanner or exploitation framework.

It does not perform:

- vulnerability exploitation
- credential attacks
- brute-force login testing
- fuzzing
- subdomain enumeration
- JavaScript/browser rendering
- screenshot capture
- historical URL collection
- unrestricted crawling of external hosts

Finding a parameter, route, redirect, or HTTP error is reconnaissance information, not proof of a security vulnerability.

## 14. Responsible use

Authorization is the boundary.

Before scanning, confirm:

- which hostnames are in scope
- which paths are in scope
- whether external-link requests are permitted
- any rate or timing restrictions
- any program-specific rules

Scryx does not treat `robots.txt` as authorization. A public website is not automatically permission to perform security testing.
