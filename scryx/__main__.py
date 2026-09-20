"""Allow `python -m scryx` as a fallback launcher."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
