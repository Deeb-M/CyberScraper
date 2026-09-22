import io
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

from scryx import __version__
from scryx import cli


class CliTests(unittest.TestCase):
    def test_parser_uses_short_command_name(self):
        self.assertEqual(cli.build_parser().prog, "scryx")

    def test_version_flag_reports_package_version(self):
        buffer = io.StringIO()
        with patch("sys.argv", ["scryx", "--version"]):
            with self.assertRaises(SystemExit) as exc, redirect_stdout(buffer):
                cli.main()
        self.assertEqual(exc.exception.code, 0)
        self.assertIn(f"Scryx {__version__}", buffer.getvalue())

    def test_no_target_prints_help_and_returns_usage_error(self):
        with patch("sys.argv", ["scryx"]):
            with io.StringIO() as buffer, redirect_stdout(buffer):
                code = cli.main()
                output = buffer.getvalue()
        self.assertEqual(code, 2)
        self.assertIn("usage: scryx", output)


class PresetTests(unittest.TestCase):
    def test_recon_preset_uses_balanced_defaults(self):
        args = cli.build_parser().parse_args(["example.com", "--recon"])
        settings = cli.resolve_scan_settings(args)

        self.assertEqual(settings["preset"], "recon")
        self.assertEqual(settings["depth"], 1)
        self.assertEqual(settings["max_pages"], 25)
        self.assertTrue(settings["check_links"])
        self.assertEqual(settings["check_limit"], 25)

    def test_explicit_values_override_deep_preset(self):
        args = cli.build_parser().parse_args(
            [
                "example.com",
                "--deep",
                "--depth",
                "1",
                "--max-pages",
                "12",
                "--no-check-links",
            ]
        )
        settings = cli.resolve_scan_settings(args)

        self.assertEqual(settings["preset"], "deep")
        self.assertEqual(settings["depth"], 1)
        self.assertEqual(settings["max_pages"], 12)
        self.assertFalse(settings["check_links"])

    def test_presets_are_mutually_exclusive(self):
        parser = cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["example.com", "--quick", "--recon"])


class ReconMapCliTests(unittest.TestCase):
    def test_recon_map_prints_grouped_routes_parameters_and_redirects(self):
        intelligence = {
            "endpoint_groups": [
                {"path": "/product", "observed_urls": 20, "parameters": ["productId"], "example_urls": ["https://example.com/product?productId=1"], "redirects": []},
                {"path": "/my-account", "observed_urls": 1, "parameters": [], "example_urls": ["https://example.com/my-account"], "redirects": ["/login"]},
            ]
        }
        with io.StringIO() as buffer, redirect_stdout(buffer):
            cli.print_recon_map(intelligence)
            output = buffer.getvalue()
        self.assertIn("[RECON MAP]", output)
        self.assertIn("Endpoint groups: 2", output)
        self.assertIn("/product (parameters: productId; observed URLs: 20)", output)
        self.assertIn("/my-account", output)
        self.assertIn("-> /login", output)



class ColorCliTests(unittest.TestCase):
    def tearDown(self):
        cli.configure_color("never")

    def test_color_option_defaults_to_auto(self):
        args = cli.build_parser().parse_args(["example.com"])
        self.assertEqual(args.color, "auto")

    def test_color_always_adds_ansi_and_never_does_not(self):
        cli.configure_color("always")
        self.assertIn("\033[36m", cli.heading("[RECON MAP]"))
        cli.configure_color("never")
        self.assertEqual(cli.heading("[RECON MAP]"), "[RECON MAP]")

    @patch("scryx.cli.sys.stdout.isatty", return_value=False)
    def test_auto_disables_color_when_output_is_not_tty(self, _mock_isatty):
        cli.configure_color("auto")
        self.assertEqual(cli.heading("[HTTP CHECKS]"), "[HTTP CHECKS]")

class ReportingCliTests(unittest.TestCase):
    def test_report_directory_option_is_available(self):
        args = cli.build_parser().parse_args(
            ["example.com", "--recon", "--report-dir", "scans"]
        )
        self.assertEqual(args.report_dir, "scans")
        self.assertFalse(args.report)

    @patch("scryx.cli.save_report", side_effect=PermissionError("denied"))
    @patch(
        "scryx.cli.scrape",
        return_value=([], "https://example.com/"),
    )
    def test_output_filesystem_error_is_reported_cleanly(
        self,
        _mock_scrape,
        _mock_save,
    ):
        with patch(
            "sys.argv",
            ["scryx", "example.com", "--output", "results.json"],
        ):
            with io.StringIO() as buffer, redirect_stdout(buffer):
                code = cli.main()
                output = buffer.getvalue()

        self.assertEqual(code, 1)
        self.assertIn("Could not save report", output)
        self.assertIn("denied", output)

    @patch(
        "scryx.cli.save_scan_bundle",
        side_effect=PermissionError("denied"),
    )
    @patch(
        "scryx.cli.scrape",
        return_value=([], "https://example.com/"),
    )
    def test_bundle_filesystem_error_is_reported_cleanly(
        self,
        _mock_scrape,
        _mock_save_bundle,
    ):
        with patch("sys.argv", ["scryx", "example.com", "--report"]):
            with io.StringIO() as buffer, redirect_stdout(buffer):
                code = cli.main()
                output = buffer.getvalue()

        self.assertEqual(code, 1)
        self.assertIn("Could not save scan bundle", output)
        self.assertIn("denied", output)

    @patch(
        "scryx.cli.save_scan_bundle",
        return_value=Path("scryx-scans/example_scan"),
    )
    @patch(
        "scryx.cli.scrape",
        return_value=([], "https://example.com/"),
    )
    def test_report_output_lists_generated_file_paths(
        self,
        _mock_scrape,
        _mock_save_bundle,
    ):
        with patch("sys.argv", ["scryx", "example.com", "--report"]):
            with io.StringIO() as buffer, redirect_stdout(buffer):
                code = cli.main()
                output = buffer.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("Saved scan bundle to scryx-scans/example_scan", output)
        self.assertIn("scryx-scans/example_scan/report.json", output)
        self.assertIn("scryx-scans/example_scan/links.csv", output)
        self.assertIn("scryx-scans/example_scan/summary.txt", output)

    def test_report_flag_uses_default_bundle_location(self):
        args = cli.build_parser().parse_args(["example.com", "--report"])
        self.assertTrue(args.report)
        self.assertIsNone(args.report_dir)


if __name__ == "__main__":
    unittest.main()
