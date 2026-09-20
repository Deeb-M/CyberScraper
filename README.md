# Scryx

Scryx is a focused web reconnaissance CLI for authorized security work. It grew from the original CyberScraper project into an installable command-line tool designed for Kali Linux and normal terminal use.

> Current development line: **v0.9.1**
>
> The repository is public. Scryx remains under active development and should be used only on systems you own or where you have explicit permission to perform reconnaissance or security testing.

## Goal

Normal use should be short and memorable:

```bash
scryx example.com --recon
```

Scryx handles the crawl, URL normalization, scope controls, URL-shape analysis, and bounded HTTP checks in one workflow while keeping conservative request limits.

## Current capabilities

- Installable Kali/Linux CLI through `pipx`
- Short global command: `scryx`
- Missing URL schemes default to HTTPS
- HTTP/HTTPS link discovery
- Relative-to-absolute URL normalization
- Duplicate and fragment removal
- Internal/external classification
- Same-host bounded crawling
- Crawl depth and page caps
- Path-prefix scope restriction
- Path-prefix exclusions
- File-extension exclusions
- Request delay and timeout controls
- Crawl error reporting
- Queue deduplication
- Secondary redirect host/path scope rejection
- URL analysis:
  - pages/routes
  - static assets/files
  - parameterized URLs
  - dynamic candidates
  - unique query-parameter names
- Bounded HTTP status checks
- Redirect reporting
- Broken/error result reporting
- JSON and CSV export
- Backward-compatible `cyberscraper.py` launcher

## Recon presets

Scryx v0.8 adds three simple presets.

### Quick

```bash
scryx example.com --quick
```

One-page discovery with lightweight defaults and no additional link-status pass.

### Recon

```bash
scryx example.com --recon
```

Balanced same-host crawl with bounded HTTP status and redirect checks.

Default recon profile:

- depth: 1
- maximum crawl requests: 25
- delay: 0.35 seconds
- HTTP check limit: 25
- external hosts are reported but not checked unless explicitly requested

### Deep

```bash
scryx example.com --deep
```

A larger but still bounded workflow.

Default deep profile:

- depth: 2
- maximum crawl requests: 75
- delay: 0.50 seconds
- HTTP check limit: 50

The hard crawler limit remains 100 pages and the hard HTTP check limit remains 50 URLs.

Explicit options can override preset values when needed.

## Kali installation

Install prerequisites:

```bash
sudo apt update
sudo apt install -y git pipx
pipx ensurepath
```

Clone and install:

```bash
git clone https://github.com/Deeb-M/CyberScraper.git
cd CyberScraper
pipx install .
```

Verify:

```bash
scryx --version
scryx --help
```

Run from any directory:

```bash
cd ~
scryx example.com --recon
```

## Updating a pipx development install

After pulling newer code:

```bash
cd CyberScraper
git pull
pipx reinstall scryx-recon
```

Then verify the installed version:

```bash
scryx --version
```

## Manual controls

The presets are the recommended normal workflow, but advanced controls remain available.

Bounded custom crawl:

```bash
scryx example.com --depth 1 --max-pages 15 --delay 0.5
```

Disable link checks even when using a preset:

```bash
scryx example.com --recon --no-check-links
```

Enable checks manually:

```bash
scryx example.com --check-links --check-limit 20
```

Check external links too:

```bash
scryx example.com --recon --check-external
```

External hosts may be status-checked only when this flag is explicitly supplied; they are never added to the crawl queue.

Restrict scope to a path:

```bash
scryx example.com/project --recon --path-prefix /project
```

Exclude noisy paths:

```bash
scryx example.com --recon \
  --exclude-path-prefix /archive \
  --exclude-path-prefix /login
```

Exclude file types:

```bash
scryx example.com --recon \
  --exclude-extension pdf \
  --exclude-extension zip
```

Save one report in JSON, enriched CSV, or TXT:

```bash
scryx example.com --recon --output results.json
scryx example.com --recon --output results.csv
scryx example.com --recon --output summary.txt
```

Create a complete timestamped scan bundle:

```bash
scryx example.com --recon --report
```

By default this creates a directory below `scryx-scans/` containing:

```text
report.json
links.csv
summary.txt
```

Use a custom base directory when needed:

```bash
scryx example.com --recon --report-dir ~/recon-reports
```

The enriched CSV includes category, URL type, query parameters, HTTP status, final URL, redirect state, broken state, and request errors when those values were checked.

## Safety limits

Scryx keeps reconnaissance deliberately bounded.

- Default manual maximum pages: 25
- Hard maximum pages: 100
- Maximum crawl depth: 2
- Default manual delay: 0.25 seconds
- Hard HTTP check limit: 50
- External hosts are never crawled
- External status checks require `--check-external`
- Redirects are followed only while they stay inside the requested host scope
- Path-restricted crawls also block redirects that escape the requested path prefix
- Cross-host redirects discovered during HTTP checks are reported but are not followed

These limits are intentional while the tool is developed and validated.

## URL-analysis terminology

Scryx uses deterministic URL-shape heuristics rather than claiming to understand application internals.

- **Static asset/file**: URL path ends in a known asset/file extension.
- **Parameterized URL**: URL contains one or more query parameters.
- **Dynamic candidate**: parameterized URL that is not classified as a static asset.
- **Page/route**: URL not classified as a static asset.

A dynamic candidate is a reconnaissance hint, not proof that the server executes dynamic code.

## Developer installation

For development on Windows, Linux, or macOS:

```bash
python -m venv .venv
```

Activate the environment, then:

```bash
pip install -e .
```

Verify:

```bash
scryx --version
```

The legacy launcher remains available during the transition:

```bash
python cyberscraper.py https://example.com
```

## Testing

Run locally:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions installs the package, compiles the project, verifies the CLI entry point, and runs the unit suite on Python 3.10, 3.12, 3.13, and 3.14.

## Project structure

```text
CyberScraper/
├── .github/
│   └── workflows/
│       └── tests.yml
├── scryx/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── core.py
│   └── reporting.py
├── tests/
│   ├── test_cli.py
│   ├── test_cyberscraper.py
│   └── test_reporting.py
├── cyberscraper.py
├── pyproject.toml
├── requirements.txt
├── README.md
└── LICENSE
```

## Milestones

**v0.7 — Kali CLI foundation:** completed. Scryx was installed through `pipx` and successfully run from outside the source directory on Kali Linux.

**v0.8 — Recon workflow:** completed. Presets, URL intelligence, bounded HTTP status/redirect checks, and safer crawl handling were validated on Kali Linux.

**v0.9 — Reporting:** completed. Timestamped scan directories, richer JSON/CSV/TXT output, concise professional summaries, and report usability were validated on Kali Linux.

**v0.9.1 — Redirect hardening:** strict same-host redirect following, blocked cross-host redirect reporting, path-scope redirect protection, malformed-HTML regression coverage, and broader redirect tests.

**v0.9.x — Remaining hardening:** timeout/HTTP edge cases, duplicate behavior, robots-awareness decisions, and broader regression coverage before the v1.0 release candidate.

**v1.0 — Public release target:** simple Kali installation, short normal workflow, stable presets, useful reports, clean documentation, and final release validation.

## Responsible use

Use Scryx only on systems you own or where you have explicit permission to perform reconnaissance or security testing. Respect scope, rate limits, target infrastructure, program rules, and applicable law.

## License

MIT License.
