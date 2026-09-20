# Scryx

Scryx is a focused web reconnaissance CLI for authorized security testing. It is the next stage of the original CyberScraper project: the engine is being packaged as a real command-line tool that can be installed and used directly on Kali Linux without VS Code and without manually managing a virtual environment.

> Current development line: **v0.7**
>
> The repository is private while the Kali-focused workflow is being built and tested.

## Goal

The target user experience is simple:

```bash
scryx https://example.com
```

Advanced controls remain available when needed, but normal use should not require remembering long command chains.

## Current capabilities

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
- JSON and CSV export
- Root URL canonicalization to avoid duplicate requests
- Backward-compatible `cyberscraper.py` launcher

## Kali installation — development build

Kali users should use `pipx`. It creates and manages the isolated Python environment automatically, so the user does not need to activate a venv.

Install the prerequisites:

```bash
sudo apt update
sudo apt install -y git pipx
pipx ensurepath
```

Clone the repository and install Scryx:

```bash
git clone https://github.com/Deeb-M/CyberScraper.git
cd CyberScraper
pipx install .
```

Verify the command:

```bash
scryx --version
scryx --help
```

Then run a scan:

```bash
scryx https://example.com
```

Because the repository is currently private, cloning it requires access to the GitHub account that owns or has permission to the repository.

## Developer installation

For development on Windows, Linux, or macOS:

```bash
python -m venv .venv
```

Activate the environment, then install the package in editable mode:

```bash
pip install -e .
```

The global-style development command is then:

```bash
scryx --version
```

The old launcher still works during the transition:

```bash
python cyberscraper.py https://example.com
```

## Usage examples

Basic scan:

```bash
scryx https://example.com
```

Same-host output only:

```bash
scryx https://example.com --internal-only
```

Bounded crawl:

```bash
scryx https://example.com --depth 1 --max-pages 10 --delay 0.5
```

Restrict crawl scope to a path:

```bash
scryx https://example.com/project --depth 1 --path-prefix /project
```

Exclude noisy paths:

```bash
scryx https://example.com --depth 1 --exclude-path-prefix /archive --exclude-path-prefix /login
```

Exclude file types:

```bash
scryx https://example.com --depth 1 --exclude-extension pdf --exclude-extension zip
```

Save a report:

```bash
scryx https://example.com --depth 1 --output results.json
```

## Safety limits

Scryx currently keeps crawling deliberately bounded:

- Default maximum pages: 25
- Hard maximum pages: 100
- Maximum crawl depth: 2
- Default delay: 0.25 seconds
- External hosts are reported but are not crawled

These limits are intentional while the tool is developed and validated for authorized reconnaissance.

## Testing

Run locally:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions installs the package and verifies the `scryx` entry point on Python 3.10, 3.12, and 3.13.

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
│   └── core.py
├── tests/
│   ├── test_cli.py
│   └── test_cyberscraper.py
├── cyberscraper.py
├── pyproject.toml
├── requirements.txt
├── README.md
└── LICENSE
```

## v0.7 milestone

The v0.7 milestone is complete when a fresh Kali installation can:

1. install Scryx with `pipx`,
2. run `scryx --version`,
3. run `scryx https://example.com`,
4. use the tool without VS Code or manual venv activation.

The next milestone will focus on recon presets and a more complete URL-analysis workflow instead of adding arbitrary flags.

## Responsible use

Use Scryx only on systems you own or where you have explicit permission to perform reconnaissance or security testing. Respect scope, rate limits, target infrastructure, and applicable rules.

## License

MIT License.
