import io
import unittest
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


class ReportingCliTests(unittest.TestCase):
    def test_report_directory_option_is_available(self):
        args = cli.build_parser().parse_args(
            ["example.com", "--recon", "--report-dir", "scans"]
        )
        self.assertEqual(args.report_dir, "scans")
        self.assertFalse(args.report)

    def test_report_flag_uses_default_bundle_location(self):
        args = cli.build_parser().parse_args(["example.com", "--report"])
        self.assertTrue(args.report)
        self.assertIsNone(args.report_dir)


if __name__ == "__main__":
    unittest.main()
