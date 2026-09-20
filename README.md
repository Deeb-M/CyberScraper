# CyberScraper

CyberScraper is a small Python command-line tool that extracts, normalizes, and classifies links from a web page. It is intended for learning, web analysis, and **authorized** cybersecurity reconnaissance.

## Features

- Fetches a target web page over HTTP or HTTPS
- Extracts links from `<a href="...">` elements
- Converts relative links into absolute URLs
- Removes URL fragments and duplicates
- Classifies links as `INTERNAL` or `EXTERNAL`
- Can restrict output to the target host
- Can restrict internal links to a specific path prefix
- Handles common request failures cleanly
- Supports a configurable request timeout

## Requirements

- Python 3.10+
- `requests`
- `beautifulsoup4`

## Installation

```bash
git clone https://github.com/Deeb-M/CyberScraper.git
cd CyberScraper
python -m venv .venv
```

Activate the virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Scan one page and classify the results:

```bash
python cyberscraper.py https://example.com
```

Show only links on the same host:

```bash
python cyberscraper.py https://example.com --internal-only
```

Restrict internal results to a project path:

```bash
python cyberscraper.py https://github.com/Deeb-M/CyberScraper --path-prefix /Deeb-M/CyberScraper
```

Combine both filters:

```bash
python cyberscraper.py https://github.com/Deeb-M/CyberScraper --internal-only --path-prefix /Deeb-M/CyberScraper
```

Set a custom timeout:

```bash
python cyberscraper.py https://example.com --timeout 5
```

Example output:

```text
[+] Found 8 unique link(s)
[+] Showing 5 link(s) after filters

[INTERNAL] (3)
https://example.com/
https://example.com/about
https://example.com/login

[EXTERNAL] (2)
https://docs.example.net/
https://status.example.net/
```

## Testing

Run the automated test suite locally with:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions also runs the syntax check and unit tests automatically for pull requests and pushes to `main`.

## Project structure

```text
CyberScraper/
├── .github/
│   └── workflows/
│       └── tests.yml
├── tests/
│   └── test_cyberscraper.py
├── cyberscraper.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## Responsible use

Use CyberScraper only on websites you own or where you have explicit permission to perform testing or reconnaissance. Respect applicable laws, terms of service, robots policies, rate limits, and the target's infrastructure.

## Roadmap

Planned improvements include:

- Export results to JSON or CSV
- Basic crawl-depth support
- Domain and extension filters
- Better logging
- Expand automated test coverage

## License

This project is released under the MIT License.
