#!/usr/bin/env python3
import logging
import os
import sqlite3
import sys

logger = logging.getLogger(__name__)

ORDERS_COLUMNS = [
    ("payment_id", "TEXT"),
    ("admin_message_id", "INTEGER"),
    ("updated_at", "DATETIME"),
]

CREATE_ORDERS = """CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    payment_id TEXT,
    admin_message_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)"""


class DatabaseMigrator:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def ensure_db_directory(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def get_table_columns(self, conn: sqlite3.Connection, table_name: str) -> list[str]:
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]

    def add_missing_columns(self, conn: sqlite3.Connection):
        existing = self.get_table_columns(conn, "orders")
        for name, column_type in ORDERS_COLUMNS:
            if name in existing:
                continue
            # sqlite refuses CURRENT_TIMESTAMP as a default in ALTER TABLE, so backfill by hand
            conn.execute(f"ALTER TABLE orders ADD COLUMN {name} {column_type}")
            if column_type == "DATETIME":
                conn.execute(f"UPDATE orders SET {name} = CURRENT_TIMESTAMP WHERE {name} IS NULL")
            logger.info(f"added column orders.{name}")

    def fix_status_spelling(self, conn: sqlite3.Connection):
        # early versions wrote the british spelling, the api says canceled
        fixed = conn.execute("UPDATE orders SET status = 'canceled' WHERE status = 'cancelled'").rowcount
        if fixed:
            logger.info(f"renamed status on {fixed} orders")

    def run_migration(self) -> bool:
        try:
            self.ensure_db_directory()
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(CREATE_ORDERS)
                self.add_missing_columns(conn)
                self.fix_status_spelling(conn)
                conn.commit()
            finally:
                conn.close()
            logger.info(f"migration done: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"migration failed: {e}")
            return False


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from config import settings

    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        logger.error("this helper only knows sqlite")
        return 1
    return 0 if DatabaseMigrator(settings.database_url[len(prefix):]).run_migration() else 1


if __name__ == "__main__":
    sys.exit(main())
