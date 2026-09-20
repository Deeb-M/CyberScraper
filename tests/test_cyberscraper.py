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
