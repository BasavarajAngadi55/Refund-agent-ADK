"""Initialize or reset the SQLite orders database.

Usage:
  python scripts/init_db.py
  python scripts/init_db.py --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import count_orders, db_path, init_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize SQLite orders database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing rows and reseed from scratch",
    )
    args = parser.parse_args()

    total = init_db(force_reseed=args.force)
    print(f"Database: {db_path()}")
    print(f"Orders loaded: {total} (current count: {count_orders()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
