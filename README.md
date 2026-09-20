# CyberScraper

CyberScraper is a small Python command-line tool that extracts and normalizes links from a web page. It is intended for learning, web analysis, and **authorized** cybersecurity reconnaissance.

## Features

- Fetches a target web page over HTTP or HTTPS
- Extracts links from `<a href="...">` elements
- Converts relative links into absolute URLs
- Removes URL fragments and duplicates
- Can restrict output to the target host
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

Scan one page:

```bash
python cyberscraper.py https://example.com
```

Show only links on the same host:

```bash
python cyberscraper.py https://example.com --internal-only
```

Set a custom timeout:

```bash
python cyberscraper.py https://example.com --timeout 5
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
