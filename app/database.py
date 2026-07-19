"""SQLite storage for retail orders."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "orders.db"

SEED_ORDERS: list[tuple[str, str, float, str, bool, str]] = [
    # order_id, purchase_date, amount, item_name, is_clearance, refund_status
    ("ORD-101", "2026-07-10", 89.99, "Premium Leather Jacket", False, "NONE"),
    ("ORD-102", "2026-05-15", 120.00, "Pro Running Shoes", False, "NONE"),
    ("ORD-103", "2026-07-14", 29.99, "Clearance Gym Tee", True, "NONE"),
    ("ORD-104", "2026-07-01", 45.50, "Cotton Hoodie", False, "NONE"),
    ("ORD-105", "2026-06-20", 199.00, "Wireless Headphones", False, "NONE"),
    ("ORD-106", "2026-07-12", 15.99, "Clearance Socks Pack", True, "NONE"),
    ("ORD-107", "2026-07-05", 64.00, "Desk Lamp", False, "REFUNDED"),
    ("ORD-108", "2026-07-16", 249.99, "Smart Watch", False, "NONE"),
    ("ORD-109", "2026-04-01", 79.00, "Winter Coat", False, "NONE"),
    ("ORD-110", "2026-06-28", 22.00, "Clearance Cap", True, "NONE"),
    ("ORD-111", "2026-07-08", 34.75, "Yoga Mat", False, "NONE"),
    ("ORD-112", "2026-05-30", 55.00, "Backpack", False, "NONE"),
    ("ORD-113", "2026-07-15", 18.50, "Clearance Water Bottle", True, "NONE"),
    ("ORD-114", "2026-06-01", 150.00, "Office Chair Cushion", False, "NONE"),
    ("ORD-115", "2026-07-11", 92.00, "Bluetooth Speaker", False, "NONE"),
    ("ORD-116", "2026-03-10", 40.00, "Garden Gloves", False, "NONE"),
    ("ORD-117", "2026-07-13", 12.99, "Clearance Keychain", True, "NONE"),
    ("ORD-118", "2026-06-25", 68.00, "Sunglasses", False, "NONE"),
    ("ORD-119", "2026-07-09", 110.00, "Running Shorts", False, "NONE"),
    ("ORD-120", "2026-05-01", 33.00, "T-Shirt", False, "NONE"),
]


def db_path() -> Path:
    configured = os.getenv("ORDERS_DB_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force_reseed: bool = False) -> int:
    """Create tables and seed orders if the database is empty."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                purchase_date TEXT NOT NULL,
                amount REAL NOT NULL,
                item_name TEXT NOT NULL,
                is_clearance INTEGER NOT NULL DEFAULT 0,
                refund_status TEXT NOT NULL DEFAULT 'NONE'
            )
            """
        )

        count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        if count > 0 and not force_reseed:
            conn.commit()
            return count

        if force_reseed:
            conn.execute("DELETE FROM orders")

        conn.executemany(
            """
            INSERT INTO orders (
                order_id, purchase_date, amount, item_name, is_clearance, refund_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    order_id,
                    purchase_date,
                    amount,
                    item_name,
                    int(is_clearance),
                    refund_status,
                )
                for order_id, purchase_date, amount, item_name, is_clearance, refund_status in SEED_ORDERS
            ],
        )
        conn.commit()
        return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]


def row_to_order(row: sqlite3.Row) -> dict:
    return {
        "purchase_date": row["purchase_date"],
        "amount": row["amount"],
        "item_name": row["item_name"],
        "is_clearance": bool(row["is_clearance"]),
        "refund_status": row["refund_status"],
    }


def get_order(order_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            (order_id.strip().upper(),),
        ).fetchone()
        if not row:
            return None
        return row_to_order(row)


def mark_refunded(order_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE orders
            SET refund_status = 'REFUNDED'
            WHERE order_id = ? AND refund_status != 'REFUNDED'
            """,
            (order_id.strip().upper(),),
        )
        conn.commit()
        return cursor.rowcount > 0


def count_orders() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
