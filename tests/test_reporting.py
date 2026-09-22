import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scryx import reporting


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "requested_url": "https://example.com",
            "final_url": "https://example.com/",
            "preset": "recon",
            "total_found": 3,
            "total_shown": 3,
            "filters": {
                "internal_only": False,
                "path_prefix": None,
                "exclude_path_prefixes": [],
                "exclude_extensions": [],
            },
            "crawl": {
                "depth": 1,
                "pages_attempted": 2,
                "pages_scanned": 2,
                "failed_requests": 0,
                "max_pages": 25,
                "errors": [],
            },
            "links": {
                "internal": [
                    "https://example.com/search?q=test",
                    "https://example.com/app.js?v=1",
                ],
                "external": ["https://external.test/page"],
            },
            "analysis": {
                "summary": {
                    "pages": 2,
                    "static_assets": 1,
                    "parameterized": 2,
                    "dynamic_candidates": 1,
                    "unique_parameters": 2,
                },
                "pages": [
                    "https://example.com/search?q=test",
                    "https://external.test/page",
                ],
                "static_assets": ["https://example.com/app.js?v=1"],
                "parameterized": [
                    {
                        "url": "https://example.com/search?q=test",
                        "parameters": ["q"],
                    },
                    {
                        "url": "https://example.com/app.js?v=1",
                        "parameters": ["v"],
                    },
                ],
                "dynamic_candidates": ["https://example.com/search?q=test"],
                "unique_parameters": ["q", "v"],
            },
            "recon_intelligence": {
                "target_host": "example.com",
                "hosts": {
                    "internal": ["example.com"],
                    "external": ["external.test"],
                    "internal_count": 1,
                    "external_count": 1,
                },
                "internal_parameterized_routes": ["https://example.com/search?q=test"],
                "internal_dynamic_candidates": ["https://example.com/search?q=test"],
                "leads": [
                    {
                        "type": "parameterized_routes",
                        "count": 1,
                        "items": ["https://example.com/search?q=test"],
                        "note": "Internal routes with query parameters were discovered.",
                    }
                ],
            },
            "http_checks": {
                "summary": {
                    "checked": 2,
                    "redirects": 1,
                    "broken": 1,
                    "errors": 0,
                },
                "results": [
                    {
                        "url": "https://example.com/search?q=test",
                        "status": 200,
                        "final_url": "https://example.com/search?q=test",
                        "redirected": False,
                        "broken": False,
                        "error": None,
                    },
                    {
                        "url": "https://external.test/page",
                        "status": 404,
                        "final_url": "https://external.test/new",
                        "redirected": True,
                        "broken": True,
                        "error": None,
                    },
                ],
            },
        }

    def test_output_formats_include_txt(self):
        self.assertEqual(reporting.output_format_for_path("report.json"), "json")
        self.assertEqual(reporting.output_format_for_path("report.csv"), "csv")
        self.assertEqual(reporting.output_format_for_path("report.txt"), "txt")

        with self.assertRaises(ValueError):
            reporting.output_format_for_path("report.html")

    def test_enriched_csv_contains_analysis_and_http_fields(self):
        rows = reporting.build_csv_rows(self.report)

        self.assertEqual(rows[0]["category"], "INTERNAL")
        self.assertEqual(rows[0]["url_type"], "PAGE")
        self.assertEqual(rows[0]["parameters"], "q")
        self.assertEqual(rows[0]["status"], 200)

        self.assertEqual(rows[1]["url_type"], "STATIC")
        self.assertEqual(rows[1]["parameters"], "v")

        self.assertEqual(rows[2]["category"], "EXTERNAL")
        self.assertEqual(rows[2]["status"], 404)
        self.assertTrue(rows[2]["redirected"])
        self.assertTrue(rows[2]["broken"])

    def test_text_report_contains_professional_summary(self):
        text = reporting.render_text_report(self.report)

        self.assertIn("Scryx Recon Report", text)
        self.assertIn("Target: https://example.com", text)
        self.assertIn("Parameterized URLs: 2", text)
        self.assertIn("Broken/error results: 1", text)
        self.assertIn("Recon Intelligence", text)
        self.assertIn("External hosts referenced: 1", text)
        self.assertIn("parameterized_routes: 1", text)
        self.assertIn("[404] https://external.test/page", text)

    def test_scan_bundle_creates_json_csv_and_txt(self):
        fixed_time = datetime(2026, 9, 20, 18, 30, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as temp_dir:
            scan_dir = reporting.save_scan_bundle(
                temp_dir,
                self.report,
                timestamp=fixed_time,
            )

            self.assertEqual(
                scan_dir.name,
                "20260920T183000Z_example.com_recon",
            )
            self.assertTrue((scan_dir / "report.json").is_file())
            self.assertTrue((scan_dir / "links.csv").is_file())
            self.assertTrue((scan_dir / "summary.txt").is_file())

            saved = json.loads((scan_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["preset"], "recon")

            with (scan_dir / "links.csv").open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["url_type"], "PAGE")

            summary = (scan_dir / "summary.txt").read_text(encoding="utf-8")
            self.assertIn("Scryx Recon Report", summary)

    def test_scan_bundle_collision_uses_incremented_suffix(self):
        fixed_time = datetime(2026, 9, 20, 18, 30, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as temp_dir:
            first = reporting.save_scan_bundle(
                temp_dir,
                self.report,
                timestamp=fixed_time,
            )
            second = reporting.save_scan_bundle(
                temp_dir,
                self.report,
                timestamp=fixed_time,
            )

            self.assertEqual(
                first.name,
                "20260920T183000Z_example.com_recon",
            )
            self.assertEqual(
                second.name,
                "20260920T183000Z_example.com_recon_2",
            )
            self.assertTrue((second / "report.json").is_file())
            self.assertTrue((second / "links.csv").is_file())
            self.assertTrue((second / "summary.txt").is_file())

    def test_individual_txt_output_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "summary.txt"
            selected = reporting.save_report(path, self.report)

            self.assertEqual(selected, "txt")
            self.assertIn(
                "Scryx Recon Report",
                path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
