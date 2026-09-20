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


if __name__ == "__main__":
    unittest.main()
