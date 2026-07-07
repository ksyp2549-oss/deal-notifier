from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS price_history (
    source TEXT NOT NULL,
    item_id TEXT NOT NULL,
    price INTEGER NOT NULL,
    observed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_price_history_item
    ON price_history (source, item_id);

CREATE TABLE IF NOT EXISTS notifications (
    source TEXT NOT NULL,
    item_id TEXT NOT NULL,
    price INTEGER NOT NULL,
    notified_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notifications_item
    ON notifications (source, item_id);
"""


class Storage:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_price(self, source: str, item_id: str, price: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO price_history (source, item_id, price, observed_at) VALUES (?, ?, ?, ?)",
                (source, item_id, price, datetime.now(timezone.utc).isoformat()),
            )

    def get_price_history_stats(self, source: str, item_id: str) -> tuple[int | None, int]:
        """Returns (min_price_before_this_observation, sample_count) excluding the most recent row."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT price FROM price_history WHERE source = ? AND item_id = ? ORDER BY observed_at DESC",
                (source, item_id),
            ).fetchall()
        if len(rows) <= 1:
            return None, len(rows)
        previous = [r[0] for r in rows[1:]]
        return min(previous), len(previous)

    def get_last_notification(self, source: str, item_id: str) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT notified_at FROM notifications WHERE source = ? AND item_id = ? "
                "ORDER BY notified_at DESC LIMIT 1",
                (source, item_id),
            ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row[0])

    def was_notified_recently(self, source: str, item_id: str, cooldown_hours: float) -> bool:
        last = self.get_last_notification(source, item_id)
        if last is None:
            return False
        return datetime.now(timezone.utc) - last < timedelta(hours=cooldown_hours)

    def record_notification(self, source: str, item_id: str, price: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO notifications (source, item_id, price, notified_at) VALUES (?, ?, ?, ?)",
                (source, item_id, price, datetime.now(timezone.utc).isoformat()),
            )
