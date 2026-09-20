import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

import cyberscraper


class NormalizeUrlTests(unittest.TestCase):
    def test_relative_url_becomes_absolute_and_fragment_is_removed(self):
        result = cyberscraper.normalize_url(
            "https://example.com/docs/index.html",
            "../login#section",
        )
        self.assertEqual(result, "https://example.com/login")

    def test_unsupported_links_are_ignored(self):
        for href in ("mailto:test@example.com", "tel:+123456", "javascript:void(0)", ""):
            with self.subTest(href=href):
                self.assertIsNone(cyberscraper.normalize_url("https://example.com", href))

    def test_placeholder_ellipsis_path_is_ignored(self):
        self.assertIsNone(
            cyberscraper.normalize_url(
                "https://github.com/Deeb-M/CyberScraper",
                "/Deeb-M/CyberScraper/blob/main/...",
            )
        )


class ExtractLinksTests(unittest.TestCase):
    def setUp(self):
        self.html = """
        <html>
          <body>
            <a href="/login">Login</a>
            <a href="/login#top">Login duplicate</a>
            <a href="https://example.com/about">About</a>
            <a href="https://external.test/page">External</a>
            <a href="mailto:admin@example.com">Email</a>
          </body>
        </html>
        """

    def test_extract_links_normalizes_and_deduplicates(self):
        links = cyberscraper.extract_links(
            self.html,
            "https://example.com/start",
        )

        self.assertEqual(
            links,
            [
                "https://example.com/about",
                "https://example.com/login",
                "https://external.test/page",
            ],
        )


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.links = [
            "https://github.com/Deeb-M/CyberScraper",
            "https://github.com/Deeb-M/CyberScraper/actions",
            "https://github.com/Deeb-M/OtherRepo",
            "https://docs.github.com/en",
            "https://support.github.com/",
        ]

    def test_classifies_same_host_as_internal(self):
        internal, external = cyberscraper.classify_links(
            self.links,
            "https://github.com/Deeb-M/CyberScraper",
        )

        self.assertEqual(
            internal,
            [
                "https://github.com/Deeb-M/CyberScraper",
                "https://github.com/Deeb-M/CyberScraper/actions",
                "https://github.com/Deeb-M/OtherRepo",
            ],
        )
        self.assertEqual(
            external,
            [
                "https://docs.github.com/en",
                "https://support.github.com/",
            ],
        )

    def test_path_prefix_restricts_only_internal_links(self):
        internal, external = cyberscraper.classify_links(
            self.links,
            "https://github.com/Deeb-M/CyberScraper",
            path_prefix="/Deeb-M/CyberScraper",
        )

        self.assertEqual(
            internal,
            [
                "https://github.com/Deeb-M/CyberScraper",
                "https://github.com/Deeb-M/CyberScraper/actions",
            ],
        )
        self.assertEqual(
            external,
            [
                "https://docs.github.com/en",
                "https://support.github.com/",
            ],
        )

    def test_path_prefix_does_not_match_similar_prefix(self):
        self.assertFalse(
            cyberscraper.path_matches_prefix(
                "https://example.com/project-other",
                "/project",
            )
        )

    def test_excluded_path_prefix_is_removed_from_internal_results(self):
        internal, external = cyberscraper.classify_links(
            [
                "https://example.com/project",
                "https://example.com/project/actions",
                "https://example.com/project/docs",
                "https://external.test/page",
            ],
            "https://example.com/project",
            path_prefix="/project",
            exclude_path_prefixes=["/project/actions"],
        )

        self.assertEqual(
            internal,
            [
                "https://example.com/project",
                "https://example.com/project/docs",
            ],
        )
        self.assertEqual(external, ["https://external.test/page"])


class CrawlTests(unittest.TestCase):
    @patch("cyberscraper.time.sleep")
    @patch("cyberscraper.scrape")
    def test_depth_one_crawls_only_internal_matching_scope(self, mock_scrape, mock_sleep):
        responses = {
            "https://example.com/project": (
                [
                    "https://example.com/project/a",
                    "https://example.com/other",
                    "https://external.test/page",
                ],
                "https://example.com/project",
            ),
            "https://example.com/project/a": (
                [
                    "https://example.com/project/b",
                    "https://external.test/second",
                ],
                "https://example.com/project/a",
            ),
        }
        mock_scrape.side_effect = lambda url, timeout=10: responses[url]

        links, final_url, pages, errors = cyberscraper.crawl(
            "https://example.com/project",
            depth=1,
            max_pages=10,
            path_prefix="/project",
            delay=0.1,
        )

        self.assertEqual(final_url, "https://example.com/project")
        self.assertEqual(
            pages,
            [
                "https://example.com/project",
                "https://example.com/project/a",
            ],
        )
        self.assertEqual(errors, [])
        self.assertIn("https://example.com/project/b", links)
        self.assertIn("https://external.test/page", links)
        requested_urls = [call.args[0] for call in mock_scrape.call_args_list]
        self.assertNotIn("https://example.com/other", requested_urls)
        self.assertNotIn("https://external.test/page", requested_urls)
        mock_sleep.assert_called_once()

    @patch("cyberscraper.scrape")
    def test_excluded_path_is_not_crawled(self, mock_scrape):
        mock_scrape.side_effect = [
            (
                [
                    "https://example.com/project/actions",
                    "https://example.com/project/docs",
                ],
                "https://example.com/project",
            ),
            ([], "https://example.com/project/docs"),
        ]

        _links, _final_url, pages, _errors = cyberscraper.crawl(
            "https://example.com/project",
            depth=1,
            max_pages=10,
            path_prefix="/project",
            exclude_path_prefixes=["/project/actions"],
            delay=0,
        )

        requested_urls = [call.args[0] for call in mock_scrape.call_args_list]
        self.assertEqual(
            requested_urls,
            [
                "https://example.com/project",
                "https://example.com/project/docs",
            ],
        )
        self.assertEqual(len(pages), 2)

    @patch("cyberscraper.scrape")
    def test_max_pages_stops_crawl(self, mock_scrape):
        mock_scrape.side_effect = [
            (
                [
                    "https://example.com/a",
                    "https://example.com/b",
                ],
                "https://example.com/",
            ),
            (["https://example.com/c"], "https://example.com/a"),
        ]

        _links, _final_url, pages, _errors = cyberscraper.crawl(
            "https://example.com/",
            depth=2,
            max_pages=2,
            delay=0,
        )

        self.assertEqual(len(pages), 2)
        self.assertEqual(mock_scrape.call_count, 2)

    @patch("cyberscraper.scrape")
    def test_secondary_request_errors_are_recorded(self, mock_scrape):
        mock_scrape.side_effect = [
            (["https://example.com/a"], "https://example.com/"),
            requests.RequestException("blocked"),
        ]

        _links, _final_url, pages, errors = cyberscraper.crawl(
            "https://example.com/",
            depth=1,
            max_pages=5,
            delay=0,
        )

        self.assertEqual(len(pages), 2)
        self.assertEqual(errors, [("https://example.com/a", "blocked")])


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.report = cyberscraper.build_report(
            requested_url="https://example.com",
            final_url="https://example.com/",
            all_links=[
                "https://example.com/about",
                "https://external.test/page",
            ],
            internal=["https://example.com/about"],
            external=["https://external.test/page"],
            internal_only=False,
            path_prefix=None,
            depth=1,
            pages_scanned=2,
            max_pages=25,
            exclude_path_prefixes=["/private"],
        )

    def test_output_format_is_inferred_from_extension(self):
        self.assertEqual(cyberscraper.output_format_for_path("results.json"), "json")
        self.assertEqual(cyberscraper.output_format_for_path("results.CSV"), "csv")

        with self.assertRaises(ValueError):
            cyberscraper.output_format_for_path("results.txt")

    def test_json_export_contains_metadata_and_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "results.json"
            selected_format = cyberscraper.save_report(path, self.report)

            self.assertEqual(selected_format, "json")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["total_found"], 2)
            self.assertEqual(saved["crawl"]["depth"], 1)
            self.assertEqual(saved["crawl"]["pages_attempted"], 2)
            self.assertEqual(saved["crawl"]["pages_scanned"], 2)
            self.assertEqual(saved["crawl"]["failed_requests"], 0)
            self.assertEqual(saved["filters"]["exclude_path_prefixes"], ["/private"])
            self.assertEqual(saved["links"]["internal"], ["https://example.com/about"])
            self.assertEqual(saved["links"]["external"], ["https://external.test/page"])

    def test_csv_export_contains_category_and_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "results.csv"
            selected_format = cyberscraper.save_report(path, self.report)

            self.assertEqual(selected_format, "csv")
            with path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(
                rows,
                [
                    {"category": "INTERNAL", "url": "https://example.com/about"},
                    {"category": "EXTERNAL", "url": "https://external.test/page"},
                ],
            )

    def test_report_counts_failed_requests_separately(self):
        report = cyberscraper.build_report(
            requested_url="https://example.com",
            final_url="https://example.com/",
            all_links=["https://example.com/about"],
            internal=["https://example.com/about"],
            external=[],
            internal_only=True,
            path_prefix=None,
            depth=1,
            pages_scanned=3,
            max_pages=5,
            crawl_errors=[("https://example.com/bad", "404 Client Error")],
        )

        self.assertEqual(report["crawl"]["pages_attempted"], 3)
        self.assertEqual(report["crawl"]["pages_scanned"], 2)
        self.assertEqual(report["crawl"]["failed_requests"], 1)
        self.assertEqual(
            report["crawl"]["errors"],
            [{"url": "https://example.com/bad", "error": "404 Client Error"}],
        )

    def test_internal_only_report_omits_external_links(self):
        report = cyberscraper.build_report(
            requested_url="https://example.com",
            final_url="https://example.com/",
            all_links=[
                "https://example.com/about",
                "https://external.test/page",
            ],
            internal=["https://example.com/about"],
            external=["https://external.test/page"],
            internal_only=True,
            path_prefix=None,
        )

        self.assertEqual(report["total_shown"], 1)
        self.assertEqual(report["links"]["external"], [])


class ScrapeTests(unittest.TestCase):
    @patch("cyberscraper.requests.get")
    def test_scrape_uses_timeout_and_response_url(self, mock_get):
        response = MagicMock()
        response.text = '<a href="/final">Final</a>'
        response.url = "https://example.com/redirected"
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        links, final_url = cyberscraper.scrape("https://example.com", timeout=7)

        self.assertEqual(links, ["https://example.com/final"])
        self.assertEqual(final_url, "https://example.com/redirected")
        mock_get.assert_called_once_with(
            "https://example.com",
            headers={"User-Agent": cyberscraper.USER_AGENT},
            timeout=7,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("cyberscraper.requests.get")
    def test_scrape_propagates_request_errors(self, mock_get):
        mock_get.side_effect = requests.RequestException("network unavailable")

        with self.assertRaises(requests.RequestException):
            cyberscraper.scrape("https://example.com")


if __name__ == "__main__":
    unittest.main()
