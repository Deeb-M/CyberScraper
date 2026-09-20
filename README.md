# CyberScraper

CyberScraper is a small Python command-line tool that extracts, normalizes, classifies, exports, and optionally crawls links from a web page. It is intended for learning, web analysis, and **authorized** cybersecurity reconnaissance.

## Features

- Fetches a target web page over HTTP or HTTPS
- Extracts links from \`<a href="...">\` elements
- Converts relative links into absolute URLs
- Removes URL fragments and duplicates
- Ignores placeholder ellipsis paths such as `/...` that are not real crawl targets
- Classifies links as \`INTERNAL\` or \`EXTERNAL\`
- Can restrict output to the target host
- Can restrict internal links and crawl scope to a path prefix
- Can exclude one or more noisy internal path prefixes from output and crawling
- Can exclude file extensions such as PDF or ZIP from output and crawl requests
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

Exclude noisy sections from both output and crawl requests:

\`\`\`bash
python cyberscraper.py https://github.com/Deeb-M/CyberScraper --depth 1 --max-pages 10 --internal-only --path-prefix /Deeb-M/CyberScraper --exclude-path-prefix /Deeb-M/CyberScraper/actions --exclude-path-prefix /Deeb-M/CyberScraper/commit
\`\`\`

Repeat `--exclude-path-prefix` for as many internal prefixes as needed.

Exclude file types from output and crawling:

\`\`\`bash
python cyberscraper.py https://example.com --depth 1 --exclude-extension pdf --exclude-extension .zip
\`\`\`

Extension matching is case-insensitive, and the leading dot is optional.

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

CyberScraper never crawls external hosts. External links can still be reported, but only same-host links are eligible for additional requests. If \`--path-prefix\` is supplied, the crawler also stays inside that path. Any prefix supplied with \`--exclude-path-prefix\` is removed from the displayed internal results and is never queued for deeper crawling. Extensions supplied with \`--exclude-extension\` are filtered from both internal and external output, and matching internal links are not queued for crawling.

The default crawl cap is 25 pages and the hard maximum is 100 pages. The default delay between crawl requests is 0.25 seconds.

Example terminal summary:

\`\`\`text
[+] Attempted 5 page(s)
[+] Successfully scanned 4 page(s)
[+] Found 137 unique link(s)
[+] Showing 54 link(s) after filters

[CRAWL ERRORS] (1)
- https://example.com/unavailable
  404 Client Error: Not Found

[INTERNAL] (54)
...
\`\`\`

Failed crawl requests do not stop the rest of the crawl. Their URL and error reason are shown in the terminal and included in JSON export.

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
    "path_prefix": null,
    "exclude_path_prefixes": [],
    "exclude_extensions": [".pdf", ".zip"]
  },
  "crawl": {
    "depth": 1,
    "pages_attempted": 3,
    "pages_scanned": 2,
    "failed_requests": 1,
    "max_pages": 25,
    "errors": [
      {
        "url": "https://example.com/unavailable",
        "error": "404 Client Error: Not Found"
      }
    ]
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

- Better logging
- Optional robots.txt awareness
- Expand automated test coverage

## License

This project is released under the MIT License.
