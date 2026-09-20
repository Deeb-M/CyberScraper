#!/usr/bin/env python3
"""Backward-compatible launcher for the original CyberScraper command."""

from scryx.core import *  # noqa: F401,F403
from scryx.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
