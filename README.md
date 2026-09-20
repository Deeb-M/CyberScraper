# CyberScraper

CyberScraper is a small Python command-line tool that extracts, normalizes, classifies, exports, and optionally crawls links from a web page. It is intended for learning, web analysis, and **authorized** cybersecurity reconnaissance.

## Features

- Fetches a target web page over HTTP or HTTPS
- Extracts links from \`<a href="...">\` elements
- Converts relative links into absolute URLs
- Removes URL fragments and duplicates
- Classifies links as \`INTERNAL\` or \`EXTERNAL\`
- Can restrict output to the target host
- Can restrict internal links and crawl scope to a path prefix
- Can export filtered results to JSON or CSV
- Supports bounded same-host crawling with depth 0–2
- Limits crawl size with \`--max-pages\`
- Adds a small delay between crawl requests
- Handles request failures cleanly
- Supports a configurable request timeout

## Requirements

- Python 3.10+
- \`requests\`
- \`beautifulsoup4\`

## Installation

\`\`\`bash
git clone https://github.com/Deeb-M/CyberScraper.git
cd CyberScraper
python -m venv .venv
\`\`\`

Activate the virtual environment and install dependencies:

\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Usage

Scan one page:

\`\`\`bash
python cyberscraper.py https://example.com
\`\`\`

Show only same-host links:

\`\`\`bash
python cyberscraper.py https://example.com --internal-only
\`\`\`

Restrict results to a project path:

\`\`\`bash
python cyberscraper.py https://github.com/Deeb-M/CyberScraper --internal-only --path-prefix /Deeb-M/CyberScraper
\`\`\`

Crawl one level deeper while staying inside that path:

\`\`\`bash
python cyberscraper.py https://github.com/Deeb-M/CyberScraper --depth 1 --max-pages 10 --internal-only --path-prefix /Deeb-M/CyberScraper
\`\`\`

Crawl up to depth 2 with the default safety limits:

\`\`\`bash
python cyberscraper.py https://example.com --depth 2
\`\`\`

Adjust the delay between crawl requests:

\`\`\`bash
python cyberscraper.py https://example.com --depth 1 --delay 0.5
\`\`\`

Save filtered results as JSON:

\`\`\`bash
python cyberscraper.py https://github.com/Deeb-M/CyberScraper --depth 1 --max-pages 10 --internal-only --path-prefix /Deeb-M/CyberScraper --output results.json
\`\`\`

Save filtered results as CSV:

\`\`\`bash
python cyberscraper.py https://github.com/Deeb-M/CyberScraper --internal-only --path-prefix /Deeb-M/CyberScraper --output results.csv
\`\`\`

Set a custom timeout:

\`\`\`bash
python cyberscraper.py https://example.com --timeout 5
\`\`\`

## Crawl behavior and limits

\`--depth 0\` scans only the starting page. \`--depth 1\` scans the starting page plus eligible links found on it. \`--depth 2\` allows one additional level.

CyberScraper never crawls external hosts. External links can still be reported, but only same-host links are eligible for additional requests. If \`--path-prefix\` is supplied, the crawler also stays inside that path.

The default crawl cap is 25 pages and the hard maximum is 100 pages. The default delay between crawl requests is 0.25 seconds.

Example terminal summary:

\`\`\`text
[+] Scanned 10 page(s)
[+] Found 132 unique link(s)
[+] Showing 46 link(s) after filters

[INTERNAL] (46)
...
\`\`\`

## JSON export

JSON includes scan metadata, active filters, crawl information, counts, errors, and categorized links.

\`\`\`json
{
  "requested_url": "https://example.com",
  "final_url": "https://example.com/",
  "total_found": 8,
  "total_shown": 5,
  "filters": {
    "internal_only": false,
    "path_prefix": null
  },
  "crawl": {
    "depth": 1,
    "pages_scanned": 3,
    "max_pages": 25,
    "errors": []
  },
  "links": {
    "internal": [],
    "external": []
  }
}
\`\`\`

## CSV export

CSV contains one row per visible result:

\`\`\`text
category,url
INTERNAL,https://example.com/about
EXTERNAL,https://status.example.net/
\`\`\`

## Testing

Run the automated test suite locally with:

\`\`\`bash
python -m unittest discover -s tests -v
\`\`\`

GitHub Actions runs syntax checks and unit tests automatically for pull requests and pushes to \`main\`.

## Project structure

\`\`\`text
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
\`\`\`

## Responsible use

Use CyberScraper only on websites you own or where you have explicit permission to perform testing or reconnaissance. Respect applicable laws, terms of service, robots policies, rate limits, and the target's infrastructure.

## Roadmap

Planned improvements include:

- Domain and extension filters
- Better logging
- Optional robots.txt awareness
- Expand automated test coverage

## License

This project is released under the MIT License.
