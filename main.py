"""Convenience entry point for MarginPilot."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from marginpilot.app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
