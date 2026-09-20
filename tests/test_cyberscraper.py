import unittest
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

    def test_internal_only_removes_external_hosts(self):
        links = cyberscraper.extract_links(
            self.html,
            "https://example.com/start",
            internal_only=True,
        )

        self.assertEqual(
            links,
            [
                "https://example.com/about",
                "https://example.com/login",
            ],
        )


class ScrapeTests(unittest.TestCase):
    @patch("cyberscraper.requests.get")
    def test_scrape_uses_timeout_and_response_url(self, mock_get):
        response = MagicMock()
        response.text = '<a href="/final">Final</a>'
        response.url = "https://example.com/redirected"
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        links = cyberscraper.scrape("https://example.com", timeout=7)

        self.assertEqual(links, ["https://example.com/final"])
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
